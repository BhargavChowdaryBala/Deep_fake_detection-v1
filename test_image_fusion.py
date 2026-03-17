import sys
import os
import cv2
import numpy as np
import torch
import uuid

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import process_video_task, processing_jobs

def create_test_image(filename):
    # Create a 224x224 image with a white circle (mock face)
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.circle(img, (112, 112), 80, (200, 200, 200), -1)
    cv2.circle(img, (80, 80), 10, (0, 0, 0), -1) # Eye
    cv2.circle(img, (144, 80), 10, (0, 0, 0), -1) # Eye
    cv2.ellipse(img, (112, 140), (30, 15), 0, 0, 180, (0, 0, 0), 2) # Mouth
    cv2.imwrite(filename, img)
    print(f"Created test image: {filename}")

if __name__ == "__main__":
    image_path = "test_image.jpg"
    if not os.path.exists(image_path):
        create_test_image(image_path)
    
    job_id = str(uuid.uuid4())
    processing_jobs[job_id] = {'status': 'processing', 'progress': 0}
    
    print(f"Starting analysis for image job: {job_id}")
    process_video_task(job_id, image_path)
    
    job = processing_jobs[job_id]
    if job['status'] == 'completed':
        print("\nIMAGE ANALYSIS COMPLETED")
        print(f"Risk Score: {job['result']['risk_score']}%")
        print(f"Forensic Report: {list(job['result']['forensic_report'].keys())}")
        # Ensure 'structural' is in the report
        if 'structural' in job['result']['forensic_report']:
            print("SUCCESS: 'structural' layer found in image report.")
        else:
            print("FAILURE: 'structural' layer MISSING in image report.")
    else:
        print(f"\nIMAGE ANALYSIS FAILED: {job.get('error', 'Unknown Error')}")
    
    # Cleanup
    if os.path.exists(image_path):
        os.remove(image_path)
