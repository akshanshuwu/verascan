from fastapi import APIRouter, UploadFile, File, HTTPException
from services.face_detection import detect_face
from models.schemas import FaceDetectionResponse

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/detect-face", response_model=FaceDetectionResponse)
async def detect_face_endpoint(file: UploadFile = File(...)):
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG, PNG, or WebP image.",
        )

    # Read and validate size
    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Image is too large. Maximum size is 10MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    try:
        result = detect_face(image_bytes)
        return FaceDetectionResponse(
            success=True,
            face={
                "image_base64": result["image_base64"],
                "bounding_box": result["bounding_box"],
                "confidence": result["confidence"],
            },
            faces_detected=result["faces_detected"],
        )
    except ValueError as e:
        return FaceDetectionResponse(
            success=False,
            faces_detected=0,
            error=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Face detection failed: {str(e)}",
        )
