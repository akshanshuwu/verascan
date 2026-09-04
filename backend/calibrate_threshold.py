"""
Threshold calibration for SFace cosine similarity.

Same-person pairs: sample face vs flipped / re-encoded variants.
Different-person pairs: sample face vs public-domain portrait (Obama official
photo, test use only) and variants.

Run: cd backend && source venv/bin/activate && python calibrate_threshold.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from PIL import Image

from services.face_recognition import embed_face, cosine_similarity

SAMPLE = "/Users/akshanshsingh/.gemini/antigravity-ide/brain/e2fa6a10-6bfa-4b15-820b-0d35ae000a95/sample_face_1788512304416.jpg"
OTHER = "/tmp/other_face.jpg"


def load(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def variant_flip_jpeg(raw: bytes, quality: int) -> bytes:
    img = Image.open(io.BytesIO(raw)).transpose(Image.FLIP_LEFT_RIGHT)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def main() -> None:
    sample = load(SAMPLE)
    other = load(OTHER)
    e_sample = embed_face(sample)
    print(f"query embedding: dim={e_sample.shape[0]} norm={np.linalg.norm(e_sample):.4f}")

    same = {
        "identical": cosine_similarity(e_sample, embed_face(sample)),
        "flipped_q90": cosine_similarity(e_sample, embed_face(variant_flip_jpeg(sample, 90))),
        "flipped_q60": cosine_similarity(e_sample, embed_face(variant_flip_jpeg(sample, 60))),
    }
    e_other = embed_face(other)
    diff = {
        "different": cosine_similarity(e_sample, e_other),
        "different_vs_flipped": cosine_similarity(embed_face(variant_flip_jpeg(sample, 90)), e_other),
    }
    print("\nSAME-PERSON similarities:")
    for k, v in same.items():
        print(f"  {k}: {v:.4f}")
    print("DIFFERENT-PERSON similarities:")
    for k, v in diff.items():
        print(f"  {k}: {v:.4f}")
    gap_low = min(same.values())
    gap_high = max(diff.values())
    print(f"\nmin(same)={gap_low:.4f}  max(different)={gap_high:.4f}")
    print("recommended conservative threshold: 0.50" if gap_high < 0.50 <= gap_low else "REVIEW: distributions overlap 0.50")


if __name__ == "__main__":
    main()
