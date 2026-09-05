import base64
import os
import requests
from serpapi import GoogleSearch

from services.face_recognition import (
    embed_face,
    verify_candidate,
    get_threshold,
)
from services.hasher import fingerprint_evidence

# Candidate image download policy (spec section 6).
CANDIDATE_TIMEOUT_S = 8
CANDIDATE_MAX_BYTES = 5 * 1024 * 1024
MAX_CANDIDATES = 8
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

SOCIAL_DOMAINS = [
    "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "facebook.com", "tiktok.com", "youtube.com", "reddit.com",
    "pinterest.com", "tumblr.com",
]


def _url_serves_image(url: str) -> bool:
    """Check the public URL actually serves image bytes (Lens gets HTML otherwise -> 0 matches)."""
    try:
        res = requests.get(
            url,
            timeout=15,
            stream=True,
            headers={"User-Agent": "VeraScan/1.0"},
        )
        if res.status_code != 200:
            return False
        ctype = (res.headers.get("Content-Type") or "").lower()
        if "image" not in ctype:
            return False
        # Peek at first chunk: must be non-empty (JPEG magic ffd8ff, PNG, WebP, ...).
        for chunk in res.iter_content(1024):
            return bool(chunk)
        return False
    except requests.RequestException:
        return False


def _upload_to_catbox(image_bytes: bytes) -> str:
    """Upload image bytes to Catbox.moe, return public URL. Raises RuntimeError on failure."""
    last_err = "unknown"
    for _ in range(3):
        try:
            files = {"fileToUpload": ("face.jpg", image_bytes, "image/jpeg")}
            data = {"reqtype": "fileupload"}
            res = requests.post("https://catbox.moe/user/api.php", files=files, data=data, timeout=30)
            url = res.text.strip()
            if res.status_code == 200 and url.startswith("https://"):
                return url
            last_err = f"{res.status_code} {url[:200]}"
        except requests.RequestException as e:
            last_err = str(e)[:160]
    raise RuntimeError(f"Catbox upload failed: {last_err}")


def _upload_to_uguu(image_bytes: bytes) -> str:
    """Fallback: upload to uguu.se, return direct image URL. Raises RuntimeError on failure."""
    try:
        files = {"files[]": ("face.jpg", image_bytes, "image/jpeg")}
        res = requests.post("https://uguu.se/upload.php", files=files, timeout=30)
        payload = res.json()
        files_out = payload.get("files") or []
        url = files_out[0].get("url", "") if files_out else ""
        if res.status_code == 200 and url.startswith("https://"):
            return url
        raise RuntimeError(f"uguu upload failed: {res.status_code} {str(payload)[:200]}")
    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(f"Image hosting upload failed: {e}")


def _upload_to_tmpfiles(image_bytes: bytes) -> str:
    """Last-resort fallback: upload to tmpfiles.org, return direct download URL."""
    try:
        files = {"file": ("face.jpg", image_bytes, "image/jpeg")}
        res = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=30)
        payload = res.json()
        url = payload.get("data", {}).get("url", "")
        if url:
            # Convert https://tmpfiles.org/123/abc.jpg -> https://tmpfiles.org/dl/123/abc.jpg
            return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        raise RuntimeError(f"tmpfiles upload failed: {payload}")
    except (requests.RequestException, ValueError) as e:
        raise RuntimeError(f"Image hosting upload failed: {e}")


def _publish_image(image_bytes: bytes) -> str:
    """Publish face crop to a public URL SerpAPI can fetch.

    Tries Catbox, then uguu.se, then tmpfiles. Each candidate URL is verified
    to actually serve image bytes first: an HTML interstitial (e.g. tmpfiles
    /dl/ links returning text/html) makes Lens return Success with 0 matches,
    which the UI would misreport as "no matching content".
    """
    errors = []
    for uploader in (_upload_to_catbox, _upload_to_uguu, _upload_to_tmpfiles):
        try:
            url = uploader(image_bytes)
        except RuntimeError as e:
            errors.append(str(e)[:120])
            continue
        if _url_serves_image(url):
            return url
        errors.append(f"{uploader.__name__}: URL did not serve image bytes")
    raise RuntimeError(
        "Could not publish image for search (all hosts failed: "
        + "; ".join(errors[:3])
        + "). Try again in a minute."
    )


def search_face(image_base64: str) -> dict:
    """
    Perform a reverse image search using SerpAPI's Google Lens endpoint.

    Takes a base64-encoded face image, discovers candidates with Google Lens,
    then independently verifies each candidate with SFace embeddings.

    Returns a dict with:
      - results: ranked candidates, each with source_url (page), image_url
        (downloaded), image_source (direct/thumbnail_fallback), faces_detected,
        similarity, match, candidate_url, usable, evidence_fingerprint
      - total_results: number of ranked candidates
      - threshold: the FACE_MATCH_THRESHOLD in effect
      - best_match: top passing candidate or None
      - evidence_fingerprint: SHA-256(source page url + image bytes) of best_match or None

    Raises RuntimeError on API failures.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY environment variable is not set.")

    # Strip the data URI prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    image_bytes = base64.b64decode(image_base64)

    # Google Lens via SerpAPI requires a PUBLIC image URL: upload the crop first.
    # Temp files are never sent directly; only the public URL is queried.
    public_url = _publish_image(image_bytes)

    params = {
        "engine": "google_lens",
        "url": public_url,
        "api_key": api_key,
    }

    search = GoogleSearch(params)
    raw_results = search.get_dict()

    if "error" in raw_results:
        err = raw_results["error"]
        if "rate" in err.lower() or "limit" in err.lower():
            raise RuntimeError("Search temporarily unavailable (rate limit). Try again in a few minutes.")
        if "invalid" in err.lower() or "api_key" in err.lower():
            raise RuntimeError("Search API key invalid.")
        raise RuntimeError(f"Search failed: {err}")

    threshold = get_threshold()

    # Query embedding once: the reference every candidate is compared against.
    try:
        query_embedding = embed_face(image_bytes)
    except ValueError as e:
        raise RuntimeError(f"Could not encode a face from the query image: {e}")

    # Parse BOTH exact matches (same photo elsewhere) and visual matches.
    # Google Lens discovery only answers "what might correspond to this image";
    # VeraScan's embedding layer independently decides "same face or not".
    seen_urls = set()
    pooled = []

    for match in raw_results.get("exact_matches", []) or []:
        link = match.get("link", "")
        if not link or link in seen_urls:
            continue
        seen_urls.add(link)
        pooled.append((_to_candidate(match, exact=True), True))

    visual = raw_results.get("visual_matches", []) or []
    social_first = sorted(
        visual[:20],
        key=lambda m: (not _is_social(m.get("link", ""))),
    )
    for match in social_first:
        link = match.get("link", "")
        if not link or link in seen_urls:
            continue
        seen_urls.add(link)
        pooled.append((_to_candidate(match, exact=False), False))

    # Verify each candidate independently (bounded pool, failures never fatal).
    verified = []
    for cand, _ in pooled[:MAX_CANDIDATES]:
        verified.append(_verify_one(cand, query_embedding, threshold))

    # Rank: verified matches first by similarity desc, then the rest
    # (scored above unscored, nulls last). Original Lens order breaks ties.
    def rank_key(c):
        sim = c["similarity"]
        return (
            0 if c["match"] else 1,
            -(sim if sim is not None else -1.0),
        )

    ranked = sorted(verified, key=rank_key)
    matches = [c for c in ranked if c["match"]]
    best = matches[0] if matches else None

    return {
        "results": ranked,
        "total_results": len(ranked),
        "threshold": threshold,
        "best_match": best,
        "evidence_fingerprint": best["evidence_fingerprint"] if best else None,
    }


def _is_social(link: str) -> bool:
    return any(d in (link or "").lower() for d in SOCIAL_DOMAINS)


def _to_candidate(match: dict, exact: bool) -> dict:
    link = match.get("link", "")
    return {
        "title": match.get("title", ""),
        "url": link,
        "source_url": link,
        "thumbnail": match.get("thumbnail", ""),
        "source": match.get("source", ""),
        "snippet": match.get("snippet", ""),
        "exact": exact,
        # Extra image URL fields SerpAPI may provide per match, kept verbatim
        # so the selection below can prefer real source images over thumbnails.
        "extra_image_urls": _extra_image_urls(match),
    }


# SerpAPI Lens items always carry `thumbnail`; some also carry a higher
# quality / original image under varying keys. Anything http(s)-valued under
# these keys is treated as a candidate source image (thumbnail excluded:
# it is always the final fallback).
EXTRA_IMAGE_KEYS = (
    "original",
    "original_image",
    "image",
    "source_image",
    "full_image",
    "large_image",
    "high_resolution",
    "src",
)


def _extra_image_urls(match: dict) -> list:
    found = []
    thumb = match.get("thumbnail", "")
    for key in EXTRA_IMAGE_KEYS:
        val = match.get(key, "")
        if (
            isinstance(val, str)
            and val.startswith(("http://", "https://"))
            and val != thumb
            and val not in found
        ):
            found.append(val)
    return found


def _image_url_chain(cand: dict) -> list:
    """Ordered (url, source_label) candidates: direct → extra → thumbnail."""
    chain = []
    link = (cand.get("url") or "").split("#", 1)[0]
    if link.lower().split("?")[0].endswith(IMAGE_EXTENSIONS):
        chain.append((link, "direct"))
    for extra in cand.get("extra_image_urls") or []:
        if extra not in [u for u, _ in chain]:
            chain.append((extra, "direct"))
    thumb = cand.get("thumbnail") or ""
    if thumb and thumb not in [u for u, _ in chain]:
        chain.append((thumb, "thumbnail_fallback"))
    return chain


def _best_image_url(cand: dict) -> str | None:
    """First URL of the priority chain (kept for backward compat / tests)."""
    chain = _image_url_chain(cand)
    return chain[0][0] if chain else None


def _download_first(chain: list) -> tuple:
    """Try each chained URL in order. Returns (url, bytes, source) or (None, None, None)."""
    for url, source in chain:
        data = _download_image(url)
        if data:
            return url, data, source
    return None, None, None


def _download_image(url: str) -> bytes | None:
    """Download a candidate image within policy limits. None on any failure."""
    try:
        res = requests.get(
            url,
            timeout=CANDIDATE_TIMEOUT_S,
            stream=True,
            headers={"User-Agent": "VeraScan/1.0"},
        )
        if res.status_code != 200:
            return None
        ctype = (res.headers.get("Content-Type") or "").lower()
        if "image" not in ctype:
            return None
        chunks = []
        total = 0
        for chunk in res.iter_content(64 * 1024):
            total += len(chunk)
            if total > CANDIDATE_MAX_BYTES:
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        return data or None
    except requests.RequestException:
        return None


def _verify_one(cand: dict, query_embedding, threshold: float) -> dict:
    """Independently verify one candidate. Never raises."""
    base = {
        **{k: v for k, v in cand.items() if k != "extra_image_urls"},
        "candidate_url": cand["url"],
        "source_url": cand["url"],
        "image_url": None,
        "image_source": None,
        "faces_detected": 0,
        "similarity": None,
        "match": False,
        "usable": False,
        "evidence_fingerprint": None,
    }
    image_url, image_bytes, image_source = _download_first(_image_url_chain(cand))
    if not image_bytes:
        return base
    # The EXACT downloaded bytes below feed both face verification and the
    # evidence fingerprint. The fingerprint binds the SOURCE PAGE URL
    # (what the chain stores as sourceUrl) to those bytes. Never the
    # image/thumbnail URL, never metadata.
    result = verify_candidate(query_embedding, image_bytes)
    faces = result["faces_detected"]
    sim = result["best_similarity"]
    matched = sim is not None and sim >= threshold
    return {
        **base,
        "image_url": image_url,
        "image_source": image_source,
        "faces_detected": faces,
        "similarity": sim,
        "match": matched,
        "usable": faces > 0 and sim is not None,
        "evidence_fingerprint": (
            fingerprint_evidence(cand["url"], image_bytes) if matched else None
        ),
    }
