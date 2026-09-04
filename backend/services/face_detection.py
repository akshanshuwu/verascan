import base64
import io
import numpy as np
from PIL import Image
import cv2


def detect_face(image_bytes: bytes) -> dict:
    """
    Detect and crop the most prominent face from an image using OpenCV Haar Cascade.

    Returns a dict with:
      - image_base64: cropped face as base64 JPEG
      - bounding_box: {x, y, w, h} in pixels
      - confidence: detection confidence score (mocked to 1.0 for Haar)
      - faces_detected: total number of faces found
    
    Raises ValueError if no face is found or image is too small.
    """
    image = Image.open(io.BytesIO(image_bytes))

    if image.width < 100 or image.height < 100:
        raise ValueError("Image is too small for reliable face detection. Minimum 100x100 pixels.")

    # Convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Convert PIL image to OpenCV format (BGR)
    img_array = np.array(image)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Load Haar Cascade from local file
    import os
    cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        raise ValueError("No face detected. Try a different photo with a clearly visible face.")

    faces_detected = len(faces)

    # Pick the largest face by area (w * h)
    best_face = max(faces, key=lambda f: f[2] * f[3])
    x, y, w, h = best_face
    confidence = 1.0 # Haar cascades don't provide confidence scores natively

    # Crop with 20% padding
    img_w, img_h = image.size
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
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
        },
        "confidence": round(confidence, 4),
        "faces_detected": faces_detected,
    }
