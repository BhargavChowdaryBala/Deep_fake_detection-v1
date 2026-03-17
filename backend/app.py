import os
import cv2
import time
import uuid
import torch
import numpy as np
import threading
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
from flask_cors import CORS
import mediapipe as mp

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max limit

# Global dictionary to store processing status/results
# In production, use Redis or a database.
processing_jobs = {}

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh_instance = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Load PyTorch Model
# Try common paths for the model file/directory
POSSIBLE_PATHS = [
    '../convnext_video.pth', 
    '../convnext_video.pth (1).zip',
    'convnext_video.pth'
]
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class DeepfakeDetector:
    def __init__(self, possible_paths, device):
        self.device = device
        self.model = None
        
        # Try finding the model in the list of possible paths
        model_path = None
        for path in possible_paths:
            full_path = os.path.join(os.path.dirname(__file__), path)
            if os.path.exists(full_path):
                model_path = full_path
                break
        
        if not model_path:
            print(f"Model not found in {possible_paths}. Using dummy.")
            self.model = "Dummy"
            return

        try:
            # torch.load can load directories or zip files of models
            self.model = torch.load(model_path, map_location=device)
            if not isinstance(self.model, dict):
                self.model.eval()
            print(f"Model loaded successfully from {model_path} onto {device}")
        except Exception as e:
            print(f"Failed to load model from {model_path}. Error: {e}")
            self.model = "Dummy"

    def predict(self, frame):
        if self.model == "Dummy" or getattr(self.model, 'eval', None) is None:
            return float(np.random.uniform(0, 10))

        try:
            img = cv2.resize(frame, (224, 224))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img / 255.0
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            img = (img - mean) / std
            img = np.transpose(img, (2, 0, 1))
            tensor = torch.tensor(img, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.model(tensor)
                probabilities = torch.nn.functional.softmax(output, dim=1)
                fake_prob = probabilities[0][1].item() * 100
                return round(fake_prob, 2)
        except Exception:
            return 50.0

detector = DeepfakeDetector(POSSIBLE_PATHS, device)

# Key landmark indices
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [78, 81, 13, 311, 308, 402, 14, 178]

def calculate_ear(landmarks, left_indices, right_indices):
    def pt(idx): return np.array([landmarks[idx].x, landmarks[idx].y])
    
    l_v1 = np.linalg.norm(pt(left_indices[1]) - pt(left_indices[5]))
    l_v2 = np.linalg.norm(pt(left_indices[2]) - pt(left_indices[4]))
    l_h = np.linalg.norm(pt(left_indices[0]) - pt(left_indices[3]))
    left_ear = (l_v1 + l_v2) / (2.0 * l_h)

    r_v1 = np.linalg.norm(pt(right_indices[1]) - pt(right_indices[5]))
    r_v2 = np.linalg.norm(pt(right_indices[2]) - pt(right_indices[4]))
    r_h = np.linalg.norm(pt(right_indices[0]) - pt(right_indices[3]))
    right_ear = (r_v1 + r_v2) / (2.0 * r_h)

    return (left_ear + right_ear) / 2.0

def calculate_mar(landmarks, indices):
    def pt(idx): return np.array([landmarks[idx].x, landmarks[idx].y])
    v1 = np.linalg.norm(pt(indices[1]) - pt(indices[7]))
    v2 = np.linalg.norm(pt(indices[2]) - pt(indices[6]))
    v3 = np.linalg.norm(pt(indices[3]) - pt(indices[5]))
    h = np.linalg.norm(pt(indices[0]) - pt(indices[4]))
    return (v1 + v2 + v3) / (3.0 * h)

def process_video_task(job_id, filepath):
    """Background task to process the video frame-by-frame."""
    try:
        processing_jobs[job_id]['status'] = 'processing'
        
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # We want to extract 1 frame every 0.5 seconds
        target_fps = 2.0
        frame_interval = int(round(fps / target_fps))
        if frame_interval == 0:
            frame_interval = 1
        
        ears = []
        mars = []
        fake_probs = []
        anomalies = []
        timeline = []
        
        current_frame = 0
        extracted_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if current_frame % frame_interval == 0:
                timestamp = current_frame / fps
                
                # 1. Prediction
                prob = detector.predict(frame)
                fake_probs.append(prob)
                
                # 2. MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh_instance.process(rgb_frame)
                
                ear = 0.0
                mar = 0.0
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    ear = calculate_ear(landmarks, LEFT_EYE, RIGHT_EYE)
                    mar = calculate_mar(landmarks, MOUTH)
                    ears.append(ear)
                    mars.append(mar)
                    
                    if prob > 60:
                        timeline.append({"time": round(timestamp, 2), "event": f"High fake prob ({prob}%)"})
                
                extracted_count += 1
                
                # Update progress
                progress = int((current_frame / total_frames) * 100)
                processing_jobs[job_id]['progress'] = progress
                
            current_frame += 1
            
        cap.release()
        
        # Analyze aggregate sequences
        avg_fake_prob = float(np.mean(fake_probs)) if fake_probs else 0.0
        risk_score = avg_fake_prob
        
        if ears:
            blink_variance = np.var(ears)
            # High variance = healthy blinking, low variance = staring/rigid
            if blink_variance < 0.0001:
                anomalies.append("Unnatural lack of eye movement across sequence")
                risk_score += 15.0
                
        if mars:
            mouth_variance = np.var(mars)
            if mouth_variance < 0.0001 and avg_fake_prob > 30:
                anomalies.append("Rigid mouth movement detected across sequence")
                risk_score += 10.0
                
        is_deepfake = risk_score > 60.0
        
        processing_jobs[job_id].update({
            'status': 'completed',
            'progress': 100,
            'result': {
                'risk_score': min(100.0, round(risk_score, 2)),
                'avg_fake_prob': round(avg_fake_prob, 2),
                'is_deepfake': is_deepfake,
                'anomalies': anomalies,
                'timeline': timeline,
                'frames_analyzed': extracted_count,
            }
        })
        
    except Exception as e:
        processing_jobs[job_id]['status'] = 'error'
        processing_jobs[job_id]['error'] = str(e)
    finally:
        # Cleanup file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
        
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if video_file:
        filename = secure_filename(video_file.filename)
        job_id = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        video_file.save(filepath)
        
        processing_jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'result': None
        }
        
        # Start background processing
        thread = threading.Thread(target=process_video_task, args=(job_id, filepath))
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': job_id, 'message': 'Video uploaded successfully'})

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in processing_jobs:
        return jsonify({'error': 'Invalid job ID'}), 404
    return jsonify(processing_jobs[job_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
