import sys
import os
import cv2
import numpy as np
import torch
import time
import uuid

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import process_video_task, processing_jobs

def create_test_video(filename, duration=2, fps=10):
    # Create a video with a white circle moving (to simulate something)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (640, 480))
    
    for i in range(duration * fps):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a "face" like object
        cv2.circle(frame, (320 + int(50 * np.sin(i/5)), 240), 100, (200, 200, 200), -1)
        cv2.circle(frame, (280 + int(50 * np.sin(i/5)), 200), 10, (0, 0, 0), -1) # Eye
        cv2.circle(frame, (360 + int(50 * np.sin(i/5)), 200), 10, (0, 0, 0), -1) # Eye
        cv2.ellipse(frame, (320 + int(50 * np.sin(i/5)), 300), (40, 20), 0, 0, 180, (0, 0, 0), 2) # Mouth
        out.write(frame)
        
    out.release()
    print(f"Created test video: {filename}")

if __name__ == "__main__":
    video_path = "test_video.mp4"
    if not os.path.exists(video_path):
        create_test_video(video_path)
    
    job_id = str(uuid.uuid4())
    processing_jobs[job_id] = {'status': 'processing', 'progress': 0}
    
    print(f"Starting analysis for job: {job_id}")
    process_video_task(job_id, video_path)
    
    job = processing_jobs[job_id]
    if job['status'] == 'completed':
        print("\nANALYSIS COMPLETED")
        print(f"Risk Score: {job['result']['risk_score']}%")
        print(f"Anomalies: {job['result']['anomalies']}")
        print(f"Forensic Notes: {job['result'].get('forensic_notes', [])}")
    else:
        print(f"\nANALYSIS FAILED: {job.get('error', 'Unknown Error')}")
    
    # Cleanup
    if os.path.exists(video_path):
        os.remove(video_path)
