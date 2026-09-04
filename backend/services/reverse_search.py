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


def _upload_to_catbox(image_bytes: bytes) -> str:
    """Upload image bytes to Catbox.moe, return public URL. Raises RuntimeError on failure."""
    try:
        files = {"fileToUpload": ("face.jpg", image_bytes, "image/jpeg")}
        data = {"reqtype": "fileupload"}
        res = requests.post("https://catbox.moe/user/api.php", files=files, data=data, timeout=30)
        url = res.text.strip()
        if res.status_code == 200 and url.startswith("https://"):
            return url
        raise RuntimeError(f"Catbox upload failed: {res.status_code} {url[:200]}")
    except requests.RequestException as e:
        raise RuntimeError(f"Image hosting upload failed: {e}")


def _upload_to_tmpfiles(image_bytes: bytes) -> str:
    """Fallback: upload to tmpfiles.org, return direct download URL."""
    try:
        files = {"file": ("face.jpg", image_bytes, "image/jpeg")}
        res = requests.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=30)
        payload = res.json()
        url = payload.get("data", {}).get("url", "")
        if url:
            # Convert https://tmpfiles.org/123/abc.jpg -> https://tmpfiles.org/dl/123/abc.jpg
            return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        raise RuntimeError(f"tmpfiles upload failed: {payload}")
    except requests.RequestException as e:
        raise RuntimeError(f"Image hosting upload failed: {e}")


def _publish_image(image_bytes: bytes) -> str:
    """Publish face crop to a public URL SerpAPI can fetch. Tries Catbox, falls back to tmpfiles."""
    try:
        return _upload_to_catbox(image_bytes)
    except RuntimeError:
        return _upload_to_tmpfiles(image_bytes)


def search_face(image_base64: str) -> dict:
    """
    Perform a reverse image search using SerpAPI's Google Lens endpoint.

    Takes a base64-encoded face image, discovers candidates with Google Lens,
    then independently verifies each candidate with SFace embeddings.

    Returns a dict with:
      - results: ranked candidates, each with faces_detected, similarity,
        match, candidate_url, image_url, usable, evidence_fingerprint
      - total_results: number of ranked candidates
      - threshold: the FACE_MATCH_THRESHOLD in effect
      - best_match: top passing candidate or None
      - evidence_fingerprint: SHA-256(url + image bytes) of best_match or None

    Raises RuntimeError on API failures.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY environment variable is not set.")

    # Strip the data URI prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    image_bytes = base64.b64decode(image_base64)

    # Google Lens via SerpAPI requires a PUBLIC image URL — upload the crop first.
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

    # Query embedding once — the reference every candidate is compared against.
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
        "thumbnail": match.get("thumbnail", ""),
        "source": match.get("source", ""),
        "snippet": match.get("snippet", ""),
        "exact": exact,
    }


def _best_image_url(cand: dict) -> str | None:
    """Prefer a direct image URL; fall back to the Lens thumbnail."""
    link = (cand.get("url") or "").split("#", 1)[0]
    if link.lower().split("?")[0].endswith(IMAGE_EXTENSIONS):
        return link
    return cand.get("thumbnail") or None


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
        **cand,
        "candidate_url": cand["url"],
        "image_url": None,
        "faces_detected": 0,
        "similarity": None,
        "match": False,
        "usable": False,
        "evidence_fingerprint": None,
    }
    image_url = _best_image_url(cand)
    if not image_url:
        return base
    image_bytes = _download_image(image_url)
    if not image_bytes:
        return base
    result = verify_candidate(query_embedding, image_bytes)
    faces = result["faces_detected"]
    sim = result["best_similarity"]
    matched = sim is not None and sim >= threshold
    return {
        **base,
        "image_url": image_url,
        "faces_detected": faces,
        "similarity": sim,
        "match": matched,
        "usable": faces > 0 and sim is not None,
        "evidence_fingerprint": (
            fingerprint_evidence(image_url, image_bytes) if matched else None
        ),
    }
