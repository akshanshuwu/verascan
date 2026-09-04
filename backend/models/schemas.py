from pydantic import BaseModel
from typing import Optional


class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class FaceData(BaseModel):
    image_base64: str
    bounding_box: BoundingBox
    confidence: float


class FaceDetectionResponse(BaseModel):
    success: bool
    face: Optional[FaceData] = None
    faces_detected: int
    error: Optional[str] = None


class SearchResult(BaseModel):
    title: str
    url: str
    thumbnail: Optional[str] = None
    source: str
    snippet: Optional[str] = None
    # Independent face-verification fields (additive; null when unverifiable).
    candidate_url: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    image_source: Optional[str] = None
    faces_detected: int = 0
    similarity: Optional[float] = None
    match: bool = False
    usable: bool = False
    evidence_fingerprint: Optional[str] = None


class SearchResponse(BaseModel):
    success: bool
    query_image: Optional[str] = None
    results: list[SearchResult] = []
    total_results: int = 0
    search_engine: str = "google_lens"
    threshold: Optional[float] = None
    best_match: Optional[SearchResult] = None
    evidence_fingerprint: Optional[str] = None
    error: Optional[str] = None


class HashRequest(BaseModel):
    # Legacy metadata scheme (kept working): SHA-256(title|url|snippet|timestamp).
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: str = ""
    timestamp: Optional[str] = None
    # Evidence scheme (preferred): SHA-256(source page URL + raw image bytes).
    # `matched_url` is a backward-compatible alias, normalized to source_url.
    source_url: Optional[str] = None
    matched_url: Optional[str] = None
    image_base64: Optional[str] = None


class HashResponse(BaseModel):
    success: bool
    hash: Optional[str] = None
    algorithm: str = "sha256"
    scheme: Optional[str] = None
    error: Optional[str] = None
