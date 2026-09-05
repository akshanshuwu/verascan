"""
VeraScan independent face-recognition layer: YuNet + SFace (OpenCV contrib).

Role: encode faces into 128-D L2-normalized embeddings and compare them with
cosine similarity (higher means more similar). Used ONLY for verification.
Candidate discovery stays with SerpAPI Google Lens.

Models (lazy-downloaded once, cached under backend/models/, git-ignored):
  - YuNet  face_detection_yunet_2023mar.onnx      (~0.22 MB)
  - SFace  face_recognition_sface_2021dec.onnx    (~36.9 MB)
Source: https://github.com/opencv/opencv_zoo (Apache-2.0)
Pinned SHA-256 checksums live in MODEL_SHA256 below.

No torch / TF / dlib / DeepFace / MediaPipe. Python 3.14 + Apple Silicon safe.
Embeddings never leave the server and are never sent to the frontend.
"""

import io
import os
import threading
import urllib.request

import cv2
import numpy as np
from PIL import Image

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"

YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/"
    "models/face_detection_yunet/" + YUNET_FILENAME
)
SFACE_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/"
    "models/face_recognition_sface/" + SFACE_FILENAME
)

# Pinned checksums of the exact files verified during integration.
MODEL_SHA256 = {
    YUNET_FILENAME: "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    SFACE_FILENAME: "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
}

EMBEDDING_DIM = 128
DEFAULT_THRESHOLD = 0.50

_detector = None
_recognizer = None
_threshold = None

# YuNet/SFace instances are shared singletons and not thread-safe:
# setInputSize() mutates shared state, so concurrent detect() calls with
# different image sizes race and crash in the DNN forward pass. Parallel
# candidate verification must serialize only the model calls; image
# decoding and downloads stay parallel.
_MODEL_LOCK = threading.Lock()


def _ensure_model(filename: str, url: str) -> str:
    """Download the model once if missing; verify checksum when pinned."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    expected = MODEL_SHA256.get(filename)
    if expected:
        h = __import__("hashlib").sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            raise RuntimeError(
                f"Checksum mismatch for {filename}: expected {expected}, "
                "refusing to load an unverified model."
            )
    return path


def get_models():
    """Load YuNet + SFace once; return (detector, recognizer)."""
    global _detector, _recognizer
    if _detector is None or _recognizer is None:
        yunet_path = _ensure_model(YUNET_FILENAME, YUNET_URL)
        sface_path = _ensure_model(SFACE_FILENAME, SFACE_URL)
        _detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320))
        _recognizer = cv2.FaceRecognizerSF.create(sface_path, "")
    return _detector, _recognizer


def get_threshold() -> float:
    """Match threshold, loaded once from FACE_MATCH_THRESHOLD (default 0.50)."""
    global _threshold
    if _threshold is None:
        try:
            _threshold = float(os.getenv("FACE_MATCH_THRESHOLD", str(DEFAULT_THRESHOLD)))
        except (TypeError, ValueError):
            _threshold = DEFAULT_THRESHOLD
    return _threshold


def _to_bgr(image_bytes: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    arr = np.array(image)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def detect_faces_for_recognition(image_bytes: bytes) -> list:
    """YuNet face boxes (largest first). Empty list when no face is found."""
    detector, _ = get_models()
    img = _to_bgr(image_bytes)
    h, w = img.shape[:2]
    with _MODEL_LOCK:
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
    if faces is None or len(faces) == 0:
        return []
    # Largest face first; full YuNet rows (box + 5 landmarks + score) preserved.
    return sorted(faces, key=lambda f: f[2] * f[3], reverse=True)


def embed_face(image_bytes: bytes) -> np.ndarray:
    """128-D L2-normalized embedding of the largest face. Raises ValueError if none."""
    detector, recognizer = get_models()
    img = _to_bgr(image_bytes)
    h, w = img.shape[:2]
    with _MODEL_LOCK:
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0:
            raise ValueError("No face detected for embedding.")
        biggest = max(faces, key=lambda f: f[2] * f[3])
        aligned = recognizer.alignCrop(img, biggest)
        feat = recognizer.feature(aligned).flatten().astype(np.float64)
    norm = float(np.linalg.norm(feat))
    if norm == 0:
        raise ValueError("Embedding has zero norm.")
    return feat / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two L2-normalized embeddings. Higher = more similar."""
    return float(np.dot(a, b))


def verify_candidate(query_embedding: np.ndarray, candidate_bytes: bytes) -> dict:
    """
    Score every face in a candidate image against the query embedding.

    Returns {faces_detected, similarities, best_similarity} where
    best_similarity is None when no face is found. Never raises for
    undecodable images: those yield faces_detected=0.
    """
    try:
        detector, recognizer = get_models()
        img = _to_bgr(candidate_bytes)
    except Exception:
        return {"faces_detected": 0, "similarities": [], "best_similarity": None}
    h, w = img.shape[:2]
    if min(h, w) < 20:
        return {"faces_detected": 0, "similarities": [], "best_similarity": None}
    with _MODEL_LOCK:
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0:
            return {"faces_detected": 0, "similarities": [], "best_similarity": None}
        sims = []
        for face in faces:
            try:
                aligned = recognizer.alignCrop(img, face)
                feat = recognizer.feature(aligned).flatten().astype(np.float64)
                norm = float(np.linalg.norm(feat))
                if norm == 0:
                    continue
                sims.append(round(cosine_similarity(query_embedding, feat / norm), 4))
            except Exception:
                continue
    if not sims:
        return {"faces_detected": len(faces), "similarities": [], "best_similarity": None}
    return {
        "faces_detected": len(faces),
        "similarities": sims,
        "best_similarity": max(sims),
    }
