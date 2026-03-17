import os
import cv2
import torch
import torch.nn as nn
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import mediapipe as mp
import threading
import uuid
import time

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- ConvNeXt Model Architecture (Full Implementation) ---
class LayerNorm(nn.Module):
    def __init__(self, normalized_shape, eps=1e-6, data_format="channels_last"):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(normalized_shape))
        self.bias = nn.Parameter(torch.zeros(normalized_shape))
        self.eps = eps
        self.data_format = data_format
        if self.data_format not in ["channels_last", "channels_first"]:
            raise NotImplementedError
        self.normalized_shape = (normalized_shape, )
    
    def forward(self, x):
        if self.data_format == "channels_last":
            return torch.nn.functional.layer_norm(x, self.normalized_shape, self.weight, self.bias, self.eps)
        elif self.data_format == "channels_first":
            u = x.mean(1, keepdim=True)
            s = (x - u).pow(2).mean(1, keepdim=True)
            x = (x - u) / torch.sqrt(s + self.eps)
            x = self.weight[:, None, None] * x + self.bias[:, None, None]
            return x

class Block(nn.Module):
    def __init__(self, dim, drop_path=0., layer_scale_init_value=1e-6):
        super().__init__()
        self.conv_dw = nn.Conv2d(dim, dim, kernel_size=7, padding=3, groups=dim)
        self.norm = LayerNorm(dim, eps=1e-6)
        self.mlp = nn.ModuleDict({
            "fc1": nn.Linear(dim, 4 * dim),
            "act": nn.GELU(),
            "fc2": nn.Linear(4 * dim, dim)
        })
        self.gamma = nn.Parameter(layer_scale_init_value * torch.ones((dim)), 
                                    requires_grad=True) if layer_scale_init_value > 0 else None
        self.drop_path = nn.Identity()

    def forward(self, x):
        input = x
        x = self.conv_dw(x)
        x = x.permute(0, 2, 3, 1)
        x = self.norm(x)
        x = self.mlp['fc1'](x)
        x = self.mlp['act'](x)
        x = self.mlp['fc2'](x)
        if self.gamma is not None:
            x = self.gamma * x
        x = x.permute(0, 3, 1, 2)
        x = input + self.drop_path(x)
        return x

class ConvNeXt(nn.Module):
    def __init__(self, in_chans=3, depths=[3, 3, 27, 3], dims=[128, 256, 512, 1024]):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_chans, dims[0], kernel_size=4, stride=4),
            LayerNorm(dims[0], eps=1e-6, data_format="channels_first")
        )
        self.stages = nn.ModuleList()
        for i in range(4):
            stage = nn.ModuleDict()
            if i > 0:
                stage['downsample'] = nn.Sequential(
                    LayerNorm(dims[i-1], eps=1e-6, data_format="channels_first"),
                    nn.Conv2d(dims[i-1], dims[i], kernel_size=2, stride=2),
                )
            stage['blocks'] = nn.Sequential(*[Block(dim=dims[i]) for _ in range(depths[i])])
            self.stages.append(stage)
        self.head = nn.ModuleDict({
            "avgpool": nn.AdaptiveAvgPool2d((1, 1)),
            "norm": LayerNorm(dims[-1], eps=1e-6, data_format="channels_last")
        })

    def forward_features(self, x):
        x = self.stem(x)
        for i in range(4):
            if 'downsample' in self.stages[i]:
                x = self.stages[i]['downsample'](x)
            x = self.stages[i]['blocks'](x)
        x = self.head['avgpool'](x)
        x = x.view(x.size(0), -1)
        return self.head['norm'](x)

    def forward(self, x):
        return self.forward_features(x)

class DeepfakeModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = ConvNeXt()
        self.classifier = nn.Sequential(
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 2)
        )

    def forward(self, x):
        x = self.backbone(x)
        return self.classifier(x)

class DeepfakeDetector:
    def __init__(self):
        self.model = DeepfakeModel()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Move to device FIRST
        self.model.to(self.device)
        self.model.eval()
        
        # USE ABSOLUTE PATH TO PREVENT LOADING FAILURES
        weights_path = r'C:\Users\bharg\Desktop\hackaton\convnext_video_fixed.pth'
        
        try:
            if os.path.exists(weights_path):
                print(f"DEBUG: Found weights at {weights_path}. Loading...")
                state_dict = torch.load(weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print("DEBUG: Deepfake Model weights loaded SUCCESSFULLY.")
            else:
                print(f"DEBUG: ERROR - Weights file NOT FOUND at {weights_path}")
        except Exception as e:
            print(f"DEBUG: ERROR - Failed to load weights from {weights_path}: {e}")
            import traceback
            traceback.print_exc()

    def predict(self, frame):
        try:
            if frame is None:
                raise ValueError("Frame is None")
            
            # CONVERT TO RGB (Model expects RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(frame_rgb, (224, 224))
            img = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
            
            # Standard ImageNet normalization
            mean = torch.tensor([0.485, 0.456, 0.406], device=self.device).view(3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225], device=self.device).view(3, 1, 1)
            img = (img - mean) / std
            img = img.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.model(img)
                # LOG RAW LOGITS
                logits = output.cpu().numpy()[0]
                prob = torch.softmax(output, dim=1)[0, 1].item() * 100
                print(f"DEBUG: Inference - Logits: {logits}, Prob: {prob:.4f}%")
            return float(prob)
        except Exception as e:
            import traceback
            print(f"--- INFERENCE ERROR DEBUG ---")
            traceback.print_exc()
            raise e

detector = DeepfakeDetector()

# --- MediaPipe Biometrics ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh_instance = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
MOUTH = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]

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
    v1 = np.linalg.norm(pt(indices[5]) - pt(indices[15]))
    v2 = np.linalg.norm(pt(indices[6]) - pt(indices[14]))
    v3 = np.linalg.norm(pt(indices[4]) - pt(indices[16]))
    h = np.linalg.norm(pt(indices[0]) - pt(indices[10]))
    return (v1 + v2 + v3) / (3.0 * h)

def analyze_facial_forensics(face_img):
    """
    Analyzes visual artifacts typical of deepfakes:
    1. Spectral Analysis (DCT) for GAN checkerboard patterns.
    2. Texture Consistency (Laplacian) for blending artifacts.
    """
    if face_img is None or face_img.size == 0:
        return {"spectral": 0, "texture": 0}
    
    # 1. Spectral Analysis
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray_resized = cv2.resize(gray, (128, 128))
    dct = cv2.dct(np.float32(gray_resized)/255.0)
    high_freq = np.abs(dct[64:, 64:])
    spectral_score = min(100.0, np.mean(high_freq) * 8000)
    
    # 2. Texture Consistency
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    texture_score = 0
    if laplacian < 120: texture_score = 45 # Blurred/Smoothed
    elif laplacian > 1500: texture_score = 30 # Over-sharpened artifacts
    
    return {
        "spectral": round(spectral_score, 2),
        "texture": round(texture_score, 2)
    }

# --- Job Status Store ---
processing_jobs = {}

def process_video_task(job_id, filepath):
    try:
        is_image = filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        
        ears = []
        mars = []
        fake_probs = []
        spectral_scores = []
        texture_scores = []
        anomalies = []
        timeline = []
        
        if is_image:
            frame = cv2.imread(filepath)
            if frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh_instance.process(rgb_frame)
                
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    h, w, _ = frame.shape
                    pts = np.array([[l.x * w, l.y * h] for l in landmarks])
                    x, y, fw, fh = cv2.boundingRect(pts.astype(np.int32))
                    
                    # Crop and Predict
                    face_crop = frame[max(0, y-10):min(h, y+fh+10), max(0, x-10):min(w, x+fw+10)]
                    prob = detector.predict(face_crop)
                    fake_probs.append(prob)
                    
                    forensics = analyze_facial_forensics(face_crop)
                    spectral_scores.append(forensics["spectral"])
                    texture_scores.append(forensics["texture"])
                    timeline.append({"time": 0, "event": "Face detected and analyzed"})
                else:
                    # Fallback if no face detected in image
                    prob = detector.predict(frame)
                    fake_probs.append(prob)
                    timeline.append({"time": 0, "event": "No face found; analyzing full frame"})
                
                processing_jobs[job_id]['progress'] = 100
        else:
            cap = cv2.VideoCapture(filepath)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            step = max(1, total_frames // 20)
            
            print(f"DEBUG: Processing Video - Total Frames: {total_frames}, Step: {step}")
            
            for i in range(0, total_frames, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret: break
                
                timestamp = i / fps
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh_instance.process(rgb_frame)
                
                if results.multi_face_landmarks:
                    print(f"DEBUG: Frame {i} - FACE DETECTED")
                    landmarks = results.multi_face_landmarks[0].landmark
                    ears.append(calculate_ear(landmarks, LEFT_EYE, RIGHT_EYE))
                    mars.append(calculate_mar(landmarks, MOUTH))
                    
                    h, w, _ = frame.shape
                    pts = np.array([[l.x * w, l.y * h] for l in landmarks])
                    bx, by, bw, bh = cv2.boundingRect(pts.astype(np.int32))
                    
                    # Crop and Predict
                    face_crop = frame[max(0, by-10):min(h, by+bh+10), max(0, bx-10):min(w, bx+bw+10)]
                    prob = detector.predict(face_crop)
                    fake_probs.append(prob)
                    
                    forensics = analyze_facial_forensics(face_crop)
                    spectral_scores.append(forensics["spectral"])
                    texture_scores.append(forensics["texture"])

                    if prob > 50:
                        timeline.append({"time": round(timestamp, 2), "event": f"Suspect pattern ({round(prob, 1)}%)"})
                else:
                    print(f"DEBUG: Frame {i} - NO FACE FOUND")
                
                processing_jobs[job_id]['progress'] = int((i / total_frames) * 100)
            cap.release()
        
        print(f"DEBUG: Final fake_probs list: {fake_probs}")
        avg_fake_prob = float(np.mean(fake_probs)) if fake_probs else 0.0
        risk_score = avg_fake_prob
        print(f"DEBUG: Final risk_score: {risk_score:.2f}")
        
        blink_variance = np.var(ears) if ears else 1.0
        mouth_variance = np.var(mars) if mars else 1.0
        
        if ears and blink_variance < 0.0001:
            anomalies.append("Unnatural lack of eye movement detected")
        
        if mars and mouth_variance < 0.0001 and avg_fake_prob > 30:
            anomalies.append("Rigid mouth movement detected across sequence")
            
        avg_spectral = float(np.mean(spectral_scores)) if spectral_scores else 0.0
        avg_texture = float(np.mean(texture_scores)) if texture_scores else 0.0
        
        if avg_spectral > 40:
            anomalies.append("Frequency-domain artifacts detected (DCT Signature)")

        prob_variance = np.var(fake_probs) if len(fake_probs) > 1 else 0.0
        if prob_variance > 400:
            anomalies.append("High temporal inconsistency (frame flickering)")

        # Direct Model-Driven Threshold
        is_deepfake = risk_score >= 50.0
        
        forensic_report = {
            "neural": {
                "label": "Neural Integrity",
                "score": avg_fake_prob,
                "status": "danger" if avg_fake_prob > 50 else ("warning" if avg_fake_prob > 25 else "secure"),
                "description": "Probability derived from ConvNeXt backbone feature maps."
            },
            "biometric": {
                "label": "Biometric Liveness",
                "score": max(0.0, min(100.0, (1 - min(blink_variance, mouth_variance) * 1000) * 100)) if ears else 0.0,
                "status": "danger" if (blink_variance < 0.0001 or mouth_variance < 0.0001) else "secure",
                "description": "Analysis of involuntary facial muscle and eye movement."
            },
            "spectral": {
                "label": "Spectral Signature",
                "score": avg_spectral,
                "status": "danger" if avg_spectral > 40 else "secure",
                "description": "Detection of GAN-specific frequency artifacts."
            },
            "temporal": {
                "label": "Temporal Stability",
                "score": min(100, prob_variance / 10),
                "status": "danger" if prob_variance > 400 else "secure",
                "description": "Prediction consistency across sequential data points."
            }
        }

        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['result'] = {
            'is_deepfake': bool(is_deepfake),
            'risk_score': float(round(risk_score, 2)),
            'avg_fake_prob': float(round(avg_fake_prob, 2)),
            'anomalies': anomalies,
            'timeline': timeline,
            'forensic_report': forensic_report
        }

    except Exception as e:
        processing_jobs[job_id]['status'] = 'error'
        processing_jobs[job_id]['error'] = str(e)
    finally:
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except: pass

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    job_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(filepath)
    
    processing_jobs[job_id] = {'status': 'processing', 'progress': 0}
    thread = threading.Thread(target=process_video_task, args=(job_id, filepath))
    thread.start()
    return jsonify({"job_id": job_id}), 200

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    job = processing_jobs.get(job_id)
    if not job: return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
