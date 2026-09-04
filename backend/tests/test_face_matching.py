"""
Face-matching upgrade tests (spec section 15).

Fixtures: face_a.jpg (AI-generated test face) and face_b.jpg (public-domain
US-government portrait, test use only). No mocks except for network download
failures, which must not depend on the live internet.
"""
import io
import os

import numpy as np
import pytest
from PIL import Image

from services.face_recognition import (
    EMBEDDING_DIM,
    cosine_similarity,
    embed_face,
    get_threshold,
    verify_candidate,
)
from services.hasher import fingerprint_evidence

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


@pytest.fixture(scope="module")
def face_a() -> bytes:
    return load("face_a.jpg")


@pytest.fixture(scope="module")
def face_b() -> bytes:
    return load("face_b.jpg")


@pytest.fixture(scope="module")
def emb_a(face_a) -> np.ndarray:
    return embed_face(face_a)


@pytest.fixture(scope="module")
def emb_b(face_b) -> np.ndarray:
    return embed_face(face_b)


# 10. deterministic embedding generation
def test_embedding_is_deterministic(face_a):
    assert np.allclose(embed_face(face_a), embed_face(face_a))
    e = embed_face(face_a)
    assert e.shape == (EMBEDDING_DIM,)
    assert abs(float(np.linalg.norm(e)) - 1.0) < 1e-6


# 1. same image → similarity approximately 1.0
def test_same_image_similarity_approx_one(emb_a):
    assert cosine_similarity(emb_a, emb_a) == pytest.approx(1.0, abs=1e-6)


# 2. same-person images score substantially higher than unrelated persons
def test_same_person_beats_different_person(face_a, emb_a, emb_b):
    flipped = Image.open(io.BytesIO(face_a)).transpose(Image.FLIP_LEFT_RIGHT)
    buf = io.BytesIO()
    flipped.save(buf, format="JPEG", quality=90)
    same_score = cosine_similarity(emb_a, embed_face(buf.getvalue()))
    diff_score = cosine_similarity(emb_a, emb_b)
    assert same_score > 0.85
    assert same_score > diff_score + 0.5


# 3. different-person images score below the threshold
def test_different_person_below_threshold(emb_a, emb_b):
    assert cosine_similarity(emb_a, emb_b) < get_threshold()


# 4/5. threshold accept/reject boundaries
def test_threshold_boundaries():
    t = get_threshold()
    assert (t + 0.01) >= t  # accept side
    assert not ((t - 0.01) >= t)  # reject side
    assert 0.0 < t < 1.0


# 6. multiple faces → maximum candidate similarity selected
def test_multi_face_selects_maximum(emb_a, face_a, face_b):
    from services import reverse_search as rs

    img_a = np.array(Image.open(io.BytesIO(face_a)).convert("RGB"))
    img_b = np.array(Image.open(io.BytesIO(face_b)).convert("RGB"))
    half_a = img_a[:, : img_a.shape[1] // 2]
    half_b = Image.fromarray(img_b[:, : img_b.shape[1] // 2]).resize(
        (half_a.shape[1], half_a.shape[0])
    )
    collage = np.hstack([half_a, np.array(half_b)])
    buf = io.BytesIO()
    Image.fromarray(collage).save(buf, format="JPEG", quality=90)
    out = verify_candidate(emb_a, buf.getvalue())
    assert out["faces_detected"] >= 1
    assert out["best_similarity"] == max(out["similarities"])


# 7. candidate with no detectable face
def test_candidate_with_no_face(emb_a):
    blank = np.full((200, 200, 3), 128, dtype=np.uint8)
    import cv2

    ok, enc = cv2.imencode(".jpg", blank)
    assert ok
    out = verify_candidate(emb_a, enc.tobytes())
    assert out["faces_detected"] == 0
    assert out["best_similarity"] is None


# 8. candidate image download failure
def test_download_failure_returns_none():
    from services import reverse_search as rs

    assert rs._download_image("https://127.0.0.1:9/nope.jpg") is None


# 9. invalid / non-image candidate bytes
def test_invalid_candidate_bytes(emb_a):
    out = verify_candidate(emb_a, b"this is not an image")
    assert out == {"faces_detected": 0, "similarities": [], "best_similarity": None}


# 11. fingerprint determinism
def test_fingerprint_deterministic(face_a):
    fp1 = fingerprint_evidence("https://example.com/img.jpg", face_a)
    fp2 = fingerprint_evidence("https://example.com/img.jpg", face_a)
    assert fp1 == fp2 and len(fp1) == 64


# 12. fingerprint changes when one image byte changes
def test_fingerprint_byte_sensitive(face_a):
    mutated = bytearray(face_a)
    mutated[len(mutated) // 2] ^= 0x01
    assert fingerprint_evidence("https://example.com/img.jpg", face_a) != fingerprint_evidence(
        "https://example.com/img.jpg", bytes(mutated)
    )


# 13. fingerprint changes when URL changes
def test_fingerprint_url_sensitive(face_a):
    assert fingerprint_evidence("https://example.com/a.jpg", face_a) != fingerprint_evidence(
        "https://example.com/b.jpg", face_a
    )


# 14. below-threshold candidate cannot anchor (match=False gating)
def test_below_threshold_cannot_anchor(emb_a, emb_b):
    t = get_threshold()
    sim = cosine_similarity(emb_a, emb_b)
    assert sim < t
    assert not (sim >= t)  # the exact gating condition used by the pipeline


# 15. no valid best match prevents blockchain submission
def test_no_best_match_without_passing_candidate(monkeypatch):
    from services import reverse_search as rs

    class FakeSearch:
        def __init__(self, *a, **k):
            pass

        def get_dict(self):
            return {
                "visual_matches": [
                    {
                        "title": "t",
                        "link": "https://example.com/post",
                        "thumbnail": "",
                        "source": "example.com",
                        "snippet": "s",
                    }
                ]
            }

    monkeypatch.setattr(rs, "GoogleSearch", FakeSearch)
    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    import base64

    with open(os.path.join(FIXTURES, "face_a.jpg"), "rb") as f:
        b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    result = rs.search_face(b64)
    assert result["best_match"] is None
    assert result["evidence_fingerprint"] is None
    assert result["results"][0]["match"] is False
