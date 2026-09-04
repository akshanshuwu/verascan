"""
Terminology regression tests: similarity scores must never be presented as
identity probability. Scans user-facing surfaces for banned phrases.
"""
import os
import re

REPO = "/Users/akshanshsingh/VeraScan"

# Misleading claims. Must not appear in user-facing copy, docs, or API text.
BANNED = [
    r"% identity",
    r"% confidence",
    r"% identical",
    r"identity confirmed",
    r"person identified",
    r"account verified",
    r"identity verified on",
    r"identity confidence",
    r"certain this is the person",
    r"confidence that this is",
    r"IDENTITY CONFIRMED",
    r"PERSON IDENTIFIED",
    r"ACCOUNT VERIFIED",
]

# User-facing surfaces (excludes historical planning docs prd.md/task docs,
# which describe, not display, product language).
SCAN_PATHS = [
    "frontend/src",
    "backend/services",
    "backend/routers",
    "backend/models",
    "README.md",
]


def collect_files():
    out = []
    for rel in SCAN_PATHS:
        root = os.path.join(REPO, rel)
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith((".js", ".py", ".md", ".css")) and "__pycache__" not in dirpath:
                    out.append(os.path.join(dirpath, fn))
    return out


def test_no_banned_terminology():
    violations = []
    for path in collect_files():
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for pat in BANNED:
            for m in re.finditer(pat, text, re.IGNORECASE):
                line = text[: m.start()].count("\n") + 1
                violations.append(f"{path}:{line}: {m.group(0)!r}")
    assert violations == [], "banned terminology found:\n" + "\n".join(violations)


def test_api_returns_raw_numerics():
    """Similarity/threshold stay numeric. Never pre-formatted as percent."""
    from models.schemas import SearchResponse, SearchResult

    r = SearchResult(
        title="t",
        url="https://example.com/p",
        source="example.com",
        similarity=0.91,
        match=True,
    )
    assert isinstance(r.similarity, float) and r.similarity == 0.91
    resp = SearchResponse(success=True, threshold=0.50)
    assert isinstance(resp.threshold, float) and resp.threshold == 0.50
