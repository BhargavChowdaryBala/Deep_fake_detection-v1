import sys
import os
import torch
import cv2
import numpy as np

# Add backend to path to import app
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app import DeepfakeDetector
    
    print("Initializing detector...")
    detector = DeepfakeDetector()
    
    if detector.model is None:
        print("FAILED: Model not loaded.")
        sys.exit(1)
        
    print("Model loaded successfully.")
    
    # Create fake frame
    frame = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    print("Running prediction...")
    prob = detector.predict(frame)
    print(f"Prediction probability: {prob:.2f}%")
    
    if prob == 50.0:
        print("WARNING: Prediction is exactly 50.0%. Still likely hitting fallback or untuned weights.")
    else:
        print("SUCCESS: Model is producing non-default values.")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
