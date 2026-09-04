import urllib.request
import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000"

def test_backend():
    print("1. Testing /api/health...")
    try:
        res = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Failed to connect to health endpoint: {e}")
        return

    print("\n2. Using generated test face image...")
    test_img_path = "/Users/akshanshsingh/.gemini/antigravity-ide/brain/e2fa6a10-6bfa-4b15-820b-0d35ae000a95/sample_face_1788512304416.jpg"
    
    print("\n3. Testing /api/detect-face...")
    try:
        with open(test_img_path, "rb") as f:
            files = {"file": ("test_face.jpg", f, "image/jpeg")}
            res = requests.post(f"{BASE_URL}/api/detect-face", files=files)
        
        print(f"Status: {res.status_code}")
        if res.status_code != 200:
            print(f"Error: {res.text}")
        else:
            data = res.json()
            print(f"Success: {data.get('success')}")
            print(f"Faces detected: {data.get('faces_detected')}")
            if data.get("face"):
                print(f"Confidence: {data['face'].get('confidence')}")
                print(f"Bounding Box: {data['face'].get('bounding_box')}")
                b64 = data['face'].get('image_base64', '')
                print(f"Image Base64 length: {len(b64)}")
    except Exception as e:
        print(f"Failed face detection test: {e}")

    print("\n4. Testing /api/hash...")
    try:
        payload = {
            "title": "Test Post",
            "url": "https://example.com/post",
            "snippet": "This is a test snippet.",
            "timestamp": "1700000000"
        }
        res = requests.post(f"{BASE_URL}/api/hash", json=payload)
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Success: {data.get('success')}")
        print(f"Hash: {data.get('hash')}")
    except Exception as e:
        print(f"Failed hash test: {e}")

    # File deletion removed
if __name__ == "__main__":
    test_backend()
