import hashlib


def fingerprint_evidence(matched_url: str, image_bytes: bytes) -> str:
    """
    Evidence fingerprint: SHA-256 over the canonical matched image URL
    (UTF-8, with any #fragment stripped) followed by the exact raw bytes
    of the downloaded candidate image used for face verification.

    Deterministic: same URL + same bytes always yield the same fingerprint;
    changing a single image byte or the URL changes it.
    """
    canonical = matched_url.split("#", 1)[0]
    return hashlib.sha256(canonical.encode("utf-8") + image_bytes).hexdigest()


def hash_data(title: str, url: str, snippet: str, timestamp: str) -> str:
    """
    Create a SHA-256 hash of the concatenated result data.

    This hash serves as a tamper-evident fingerprint that gets stored
    on the blockchain. If any field changes, the hash changes.
    """
    combined = f"{title}|{url}|{snippet}|{timestamp}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
