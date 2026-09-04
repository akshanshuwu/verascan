from fastapi import APIRouter
from services.hasher import hash_data
from models.schemas import HashRequest, HashResponse

router = APIRouter()


@router.post("/hash", response_model=HashResponse)
async def hash_endpoint(request: HashRequest):
    try:
        data_hash = hash_data(
            title=request.title,
            url=request.url,
            snippet=request.snippet,
            timestamp=request.timestamp,
        )
        return HashResponse(
            success=True,
            hash=data_hash,
        )
    except Exception as e:
        return HashResponse(
            success=False,
            error=str(e),
        )
