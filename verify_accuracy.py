import numpy as np
import cv2

# Mock Enhanced Logic from app.py
def calculate_ear_mock(landmarks):
    # Dummy EAR values
    return 0.25, 0.26 # Mostly synchronous

def analyze_facial_forensics_mock(face_img, full_frame):
    # DCT mismatch mock
    gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    dct_face = cv2.dct(np.float32(cv2.resize(gray_face, (128, 128)))/255.0)
    bg_patch = full_frame[0:64, 0:64]
    gray_bg = cv2.cvtColor(bg_patch, cv2.COLOR_BGR2GRAY)
    dct_bg = cv2.dct(np.float32(cv2.resize(gray_bg, (128, 128)))/255.0)
    diff = np.abs(np.mean(np.abs(dct_face[0:32, 0:32])) - np.mean(np.abs(dct_bg[0:32, 0:32])))
    mismatch_score = min(100.0, diff * 500)
    return {"mismatch": mismatch_score}

# Test Sequence
dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
dummy_face = dummy_frame[100:300, 100:300]

fake_probs = [80, 85, 90, 10, 88] # Isolated drop at index 3
sustained_fake_count = sum(1 for p in fake_probs if p > 70)
sustained_factor = min(1.2, 1.0 + (sustained_fake_count / len(fake_probs)))
avg_fake_prob = np.mean(fake_probs)
risk_score = min(100.0, avg_fake_prob * sustained_factor)

print(f"Avg Prob: {avg_fake_prob:.2f}")
print(f"Sustained Count: {sustained_fake_count}")
print(f"Sustained Factor: {sustained_factor:.2f}")
print(f"Weighted Risk Score: {risk_score:.2f}")

# Symmetry Check
left_ears = [0.25, 0.25, 0.10, 0.25]
right_ears = [0.25, 0.10, 0.25, 0.25] # Asynchronous blinks!
symmetry_errors = sum(1 for l, r in zip(left_ears, right_ears) if abs(l-r) > 0.15)
print(f"Symmetry Errors: {symmetry_errors}")

# Mismatch Check
forensics = analyze_facial_forensics_mock(dummy_face, dummy_frame)
print(f"Spectral Mismatch: {forensics['mismatch']:.2f}")
