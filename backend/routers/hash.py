from fastapi import APIRouter
from services.hasher import hash_data, fingerprint_evidence
from models.schemas import HashRequest, HashResponse
import base64

router = APIRouter()


@router.post("/hash", response_model=HashResponse)
async def hash_endpoint(request: HashRequest):
    try:
        # Preferred: evidence fingerprint over the actual matched bytes,
        # bound to the SOURCE PAGE URL (what the chain stores as sourceUrl).
        source_page_url = request.source_url or request.matched_url
        if source_page_url and request.image_base64:
            raw_b64 = request.image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            image_bytes = base64.b64decode(raw_b64)
            if not image_bytes:
                return HashResponse(success=False, error="image_base64 decoded to empty bytes.")
            return HashResponse(
                success=True,
                hash=fingerprint_evidence(source_page_url, image_bytes),
                scheme="source_url + image_bytes",
            )
        # Legacy: metadata-only fingerprint (backward compatible).
        if request.title is not None and request.url is not None and request.timestamp is not None:
            data_hash = hash_data(
                title=request.title,
                url=request.url,
                snippet=request.snippet,
                timestamp=request.timestamp,
            )
            return HashResponse(
                success=True,
                hash=data_hash,
                scheme="title|url|snippet|timestamp (legacy)",
            )
        return HashResponse(
            success=False,
            error="Provide either {source_url, image_base64} (matched_url accepted as alias) or {title, url, timestamp}.",
        )
    except Exception as e:
        return HashResponse(
            success=False,
            error=str(e),
        )
