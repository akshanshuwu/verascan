"""
Evidence image selection tests: the ACTUAL source image must be verified and
fingerprinted. Lens thumbnails only as a clearly-marked final fallback.
"""
import base64
import os

import numpy as np

from services import reverse_search as rs
from services.face_recognition import embed_face
from services.hasher import fingerprint_evidence

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def make_cand(url="https://example.com/post", thumb="https://enc-tbn/x", **kw):
    return {
        "title": "t",
        "url": url,
        "source_url": url,
        "thumbnail": thumb,
        "source": "example.com",
        "snippet": "s",
        "exact": False,
        "extra_image_urls": [],
        **kw,
    }


# 1. direct image URL selection
def test_direct_image_url_selected_first():
    cand = make_cand(url="https://cdn.example.com/pic.JPG?size=1")
    chain = rs._image_url_chain(cand)
    assert chain[0] == ("https://cdn.example.com/pic.JPG?size=1", "direct")


# 2. extra SerpAPI image field preferred over thumbnail
def test_extra_image_field_beats_thumbnail():
    cand = make_cand(
        url="https://social.example.com/post/123",
        extra_image_urls=["https://cdn.example.com/original.jpg"],
    )
    chain = rs._image_url_chain(cand)
    assert chain[0] == ("https://cdn.example.com/original.jpg", "direct")
    assert chain[-1][1] == "thumbnail_fallback"


# 3. thumbnail fallback when nothing better exists
def test_thumbnail_fallback_last():
    cand = make_cand()
    chain = rs._image_url_chain(cand)
    assert chain == [("https://enc-tbn/x", "thumbnail_fallback")]
    assert rs._image_url_chain(make_cand(url="", thumb="")) == []


# 4. source page URL vs downloaded image URL kept separate
def test_source_url_vs_image_url_separate(monkeypatch):
    img = load("face_a.jpg")
    monkeypatch.setattr(rs, "_download_image", lambda url: img)
    q = embed_face(img)
    out = rs._verify_one(make_cand(url="https://social.example.com/post/9"), q, 0.50)
    assert out["source_url"] == "https://social.example.com/post/9"
    assert out["candidate_url"] == "https://social.example.com/post/9"
    assert out["image_url"] == "https://enc-tbn/x"
    assert out["image_url"] != out["source_url"]
    assert out["image_source"] == "thumbnail_fallback"


# 5. verified + fingerprinted bytes are exactly the downloaded bytes,
#    bound to the SOURCE PAGE URL (not the image URL)
def test_bytes_identical_for_verify_and_fingerprint(monkeypatch):
    img = load("face_a.jpg")
    seen = {}

    def fake_download(url):
        return img

    def fake_verify(query_emb, candidate_bytes):
        seen["bytes"] = candidate_bytes
        return {"faces_detected": 1, "similarities": [0.99], "best_similarity": 0.99}

    monkeypatch.setattr(rs, "_download_image", fake_download)
    monkeypatch.setattr(rs, "verify_candidate", fake_verify)
    q = embed_face(img)
    page = "https://social.example.com/post/9"
    out = rs._verify_one(make_cand(url=page), q, 0.50)
    assert seen["bytes"] == img
    assert out["match"] is True
    assert out["evidence_fingerprint"] == fingerprint_evidence(page, img)
    # Binding is to the source page, NOT the downloaded image URL:
    assert out["image_url"] != page
    assert out["evidence_fingerprint"] != fingerprint_evidence(out["image_url"], img)


# 6. failed downloads never become best_matchdef test_failed_downloads_never_best_match(monkeypatch):
    class FakeSearch:
        def __init__(self, *a, **k):
            pass

        def get_dict(self):
            return {
                "visual_matches": [
                    {
                        "title": "t1",
                        "link": "https://example.com/a",
                        "thumbnail": "https://enc-tbn/a",
                        "source": "example.com",
                        "snippet": "s",
                    },
                    {
                        "title": "t2",
                        "link": "https://example.com/b.jpg",
                        "thumbnail": "https://enc-tbn/b",
                        "source": "example.com",
                        "snippet": "s",
                    },
                ]
            }

    monkeypatch.setattr(rs, "GoogleSearch", FakeSearch)
    monkeypatch.setattr(rs, "_download_image", lambda url: None)
    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    with open(os.path.join(FIXTURES, "face_a.jpg"), "rb") as f:
        b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    out = rs.search_face(b64)
    assert out["best_match"] is None
    assert out["evidence_fingerprint"] is None
    assert all(c["match"] is False for c in out["results"])


# 7. URL fragment normalization: same page with/without #fragment → same hash
def test_fragment_normalization():
    from services.hasher import canonical_source_url

    img = load("face_a.jpg")
    assert canonical_source_url("https://example.com/post#comments") == "https://example.com/post"
    assert fingerprint_evidence("https://example.com/post#comments", img) == fingerprint_evidence(
        "https://example.com/post", img
    )
    # Query strings are preserved byte-for-byte (no arbitrary rewriting):
    assert fingerprint_evidence("https://example.com/post?a=1", img) != fingerprint_evidence(
        "https://example.com/post?a=2", img
    )


# 8. raw bytes are hashed. Never the base64 text of the image
def test_no_base64_string_hashing():
    import hashlib

    img = load("face_a.jpg")
    url = "https://example.com/post"
    b64_text = base64.b64encode(img).decode()
    as_text_hash = hashlib.sha256(url.encode("utf-8") + b64_text.encode("utf-8")).hexdigest()
    assert fingerprint_evidence(url, img) != as_text_hash


# 9. /api/search fingerprint is identical to what /api/store receives:
#    the same function output flows through unchanged (source page + bytes)
def test_search_fingerprint_equals_store_input(monkeypatch):
    img = load("face_a.jpg")
    page = "https://social.example.com/post/9"

    def fake_download(url):
        return img

    def fake_verify(query_emb, candidate_bytes):
        return {"faces_detected": 1, "similarities": [0.99], "best_similarity": 0.99}

    monkeypatch.setattr(rs, "_download_image", fake_download)
    monkeypatch.setattr(rs, "verify_candidate", fake_verify)
    q = embed_face(img)
    out = rs._verify_one(make_cand(url=page), q, 0.50)
    # What /api/search returns...
    search_fp = out["evidence_fingerprint"]
    # ...is exactly what /api/hash recomputes for /api/store input:
    from fastapi.testclient import TestClient

    try:
        from main import app

        client = TestClient(app)
        r = client.post(
            "/api/hash",
            json={"source_url": page, "image_base64": base64.b64encode(img).decode()},
        )
        assert r.status_code == 200
        assert r.json()["hash"] == search_fp
    except ImportError:
        # fastapi.testclient (httpx) not installed. Compare against the
        # canonical function directly instead.
        assert search_fp == fingerprint_evidence(page, img)
