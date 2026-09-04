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


class SearchResponse(BaseModel):
    success: bool
    query_image: Optional[str] = None
    results: list[SearchResult] = []
    total_results: int = 0
    search_engine: str = "google_lens"
    error: Optional[str] = None


class HashRequest(BaseModel):
    title: str
    url: str
    snippet: str = ""
    timestamp: str


class HashResponse(BaseModel):
    success: bool
    hash: Optional[str] = None
    algorithm: str = "sha256"
    error: Optional[str] = None
