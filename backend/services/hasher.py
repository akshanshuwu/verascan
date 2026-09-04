import hashlib


def hash_data(title: str, url: str, snippet: str, timestamp: str) -> str:
    """
    Create a SHA-256 hash of the concatenated result data.

    This hash serves as a tamper-evident fingerprint that gets stored
    on the blockchain. If any field changes, the hash changes.
    """
    combined = f"{title}|{url}|{snippet}|{timestamp}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
