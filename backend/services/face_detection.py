import base64
import io
import numpy as np
from PIL import Image
import mediapipe as mp


def detect_face(image_bytes: bytes) -> dict:
    """
    Detect and crop the most prominent face from an image using MediaPipe.

    Returns a dict with:
      - image_base64: cropped face as base64 JPEG
      - bounding_box: {x, y, w, h} in pixels
      - confidence: detection confidence score
      - faces_detected: total number of faces found
    
    Raises ValueError if no face is found or image is too small.
    """
    image = Image.open(io.BytesIO(image_bytes))

    if image.width < 100 or image.height < 100:
        raise ValueError("Image is too small for reliable face detection. Minimum 100x100 pixels.")

    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")

    img_array = np.array(image)

    # Use MediaPipe Face Detection
    mp_face_detection = mp.solutions.face_detection

    with mp_face_detection.FaceDetection(
        model_selection=1,  # 1 = full range model (better for varied distances)
        min_detection_confidence=0.5,
    ) as face_detection:
        results = face_detection.process(img_array)

    if not results.detections:
        raise ValueError("No face detected. Try a different photo with a clearly visible face.")

    faces_detected = len(results.detections)

    # Pick the detection with highest confidence
    best_detection = max(results.detections, key=lambda d: d.score[0])
    bbox_relative = best_detection.location_data.relative_bounding_box
    confidence = float(best_detection.score[0])

    # Convert relative bbox to absolute pixel coordinates
    img_w, img_h = image.size
    x = int(bbox_relative.xmin * img_w)
    y = int(bbox_relative.ymin * img_h)
    w = int(bbox_relative.width * img_w)
    h = int(bbox_relative.height * img_h)

    # Crop with 20% padding
    pad_x = int(w * 0.2)
    pad_y = int(h * 0.2)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(img_w, x + w + pad_x)
    y2 = min(img_h, y + h + pad_y)

    cropped = image.crop((x1, y1, x2, y2))

    # Encode to base64 JPEG
    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=90)
    face_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "image_base64": f"data:image/jpeg;base64,{face_b64}",
        "bounding_box": {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
        },
        "confidence": round(confidence, 4),
        "faces_detected": faces_detected,
    }
