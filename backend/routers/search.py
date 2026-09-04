from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.reverse_search import search_face
from models.schemas import SearchResponse

router = APIRouter()


class SearchRequest(BaseModel):
    image_base64: str


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    if not request.image_base64:
        raise HTTPException(
            status_code=400,
            detail="image_base64 is required.",
        )

    try:
        result = search_face(request.image_base64)
        return SearchResponse(
            success=True,
            query_image=request.image_base64[:100] + "...",  # Truncated for response
            results=result["results"],
            total_results=result["total_results"],
            threshold=result.get("threshold"),
            best_match=result.get("best_match"),
            evidence_fingerprint=result.get("evidence_fingerprint"),
        )
    except RuntimeError as e:
        return SearchResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )
