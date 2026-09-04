import hashlib


def canonical_source_url(source_page_url: str) -> str:
    """
    Deterministic canonicalization of the source page URL.

    Rules (exactly these, nothing more):
      - strip any URL fragment ("#..." and everything after it)
      - strip surrounding whitespace
      - query parameters, scheme/host casing, and trailing slashes are
        preserved byte-for-byte (no arbitrary rewriting)

    Returns the canonical URL string (still a str; callers UTF-8 encode it).
    """
    return source_page_url.strip().split("#", 1)[0]


def fingerprint_evidence(source_page_url: str, image_bytes: bytes) -> str:
    """
    Canonical evidence fingerprint.

        fingerprint = SHA-256(UTF-8(canonical source page URL)
                              + raw downloaded candidate image bytes)

    - source_page_url: the web/social page containing the discovered
      evidence (NOT the image URL — the chain's `sourceUrl` holds this page).
    - image_bytes: the exact raw bytes downloaded and used for face
      verification (never thumbnails-of-something-else, never metadata,
      never title/snippet/timestamp, never base64 text, never re-encoded).

    Deterministic: same canonical URL + same bytes always yield the same
    fingerprint; changing one image byte or the URL changes it.
    """
    canonical = canonical_source_url(source_page_url)
    return hashlib.sha256(canonical.encode("utf-8") + image_bytes).hexdigest()


def hash_data(title: str, url: str, snippet: str, timestamp: str) -> str:
    """
    Create a SHA-256 hash of the concatenated result data.

    This hash serves as a tamper-evident fingerprint that gets stored
    on the blockchain. If any field changes, the hash changes.
    """
    combined = f"{title}|{url}|{snippet}|{timestamp}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
