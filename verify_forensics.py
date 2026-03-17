import numpy as np
import cv2
import os

# Mock classes and functions from app.py
def analyze_facial_forensics(face_img):
    if face_img is None or face_img.size == 0:
        return {"spectral": 0, "texture": 0}
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray_resized = cv2.resize(gray, (128, 128))
    dct = cv2.dct(np.float32(gray_resized)/255.0)
    high_freq = np.abs(dct[64:, 64:])
    spectral_score = min(100.0, np.mean(high_freq) * 8000)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    texture_score = 0
    if laplacian < 100: texture_score = 40
    elif laplacian > 1500: texture_score = 30
    return {"spectral": round(spectral_score, 2), "texture": round(texture_score, 2)}

# Test with dummy data
dummy_face = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
forensics = analyze_facial_forensics(dummy_face)
print(f"Forensics on Noise: {forensics}")

fake_probs = [10, 80, 20, 90] # High variance
blink_variance = 0.00005 # Low variance
mouth_variance = 0.1

prob_variance = np.var(fake_probs)
print(f"Prob Variance: {prob_variance}")

# Mock Report Generation
forensic_report = {
    "neural": {
        "label": "Neural Integrity",
        "score": np.mean(fake_probs),
        "status": "danger" if np.mean(fake_probs) > 60 else "secure",
        "description": "Probability based on ConvNeXt-Base feature maps."
    },
    "biometric": {
        "label": "Biometric Liveness",
        "score": (1 - min(blink_variance, mouth_variance) * 1000) * 100,
        "status": "danger" if (blink_variance < 0.0001 or mouth_variance < 0.0001) else "secure",
        "description": "Analysis of blinking and mouth movement patterns."
    },
    "spectral": {
        "label": "Spectral Signature",
        "score": forensics["spectral"],
        "status": "danger" if forensics["spectral"] > 40 else "secure",
        "description": "Detection of frequency-domain GAN artifacts (DCT)."
    },
    "temporal": {
        "label": "Temporal Stability",
        "score": min(100, prob_variance / 10),
        "status": "danger" if prob_variance > 400 else "secure",
        "description": "Frame-to-frame prediction consistency check."
    }
}

print("Forensic Report Sample:")
for k, v in forensic_report.items():
    print(f"  {v['label']}: {v['status']} ({v['score']:.2f}%)")
