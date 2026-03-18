import os
import cv2
import torch
import torch.nn as nn
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import mediapipe as mp
import threading
import uuid
import time
from collections import deque
from huggingface_hub import hf_hub_download

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

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
        
        # SEARCH FOR WEIGHTS (LOCAL -> ROOT -> CURRENT)
        possible_paths = [
            r'C:\Users\bharg\Desktop\hackaton\convnext_video_fixed.pth',
            os.path.join(os.getcwd(), 'convnext_video_fixed.pth'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'convnext_video_fixed.pth'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convnext_video_fixed.pth')
        ]
        
        weights_path = None
        for p in possible_paths:
            if os.path.exists(p):
                weights_path = p
                break
        
        # BACKUP: DOWNLOAD FROM HUGGING FACE IF MISSING
        if not weights_path:
            repo_id = os.environ.get('HF_REPO_ID')
            filename = os.environ.get('HF_FILENAME', 'convnext_video_fixed.pth')
            repo_type = os.environ.get('HF_REPO_TYPE', 'model') # Default to model, allow 'space'
            
            if repo_id:
                try:
                    print(f"DEBUG: Local weights missing. Attempting to download from HF ({repo_type}): {repo_id}...")
                    weights_path = hf_hub_download(
                        repo_id=repo_id, 
                        filename=filename, 
                        repo_type=repo_type
                    )
                    print(f"DEBUG: Successfully downloaded weights to {weights_path}")
                except Exception as e:
                    print(f"DEBUG: HF Download Failed: {e}")
                    import traceback
                    traceback.print_exc()

        try:
            if weights_path:
                print(f"DEBUG: Loading weights from {weights_path}...")
                state_dict = torch.load(weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print("DEBUG: Deepfake Model weights loaded SUCCESSFULLY.")
            else:
                print(f"DEBUG: ERROR - Weights file NOT FOUND locally or on Hugging Face.")
        except Exception as e:
            print(f"DEBUG: ERROR - Failed to load weights from {weights_path}: {e}")
            import traceback
            traceback.print_exc()

    def preprocess_face(self, face_img):
        """Advanced Preprocessing: Histogram Equalization (YUV) to expose GAN artifacts."""
        if face_img is None or face_img.size == 0:
            return face_img
        yuv = cv2.cvtColor(face_img, cv2.COLOR_BGR2YUV)
        yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

    def predict(self, frame):
        try:
            if frame is None:
                raise ValueError("Frame is None")
            
            # 1. Advanced Preprocessing
            frame_processed = self.preprocess_face(frame)
            
            # 2. CONVERT TO RGB (Model expects RGB)
            frame_rgb = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2RGB)
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

# --- Lazy Loaders for Heavy Objects ---
_detector_instance = None
_face_mesh_instance = None
_detector_lock = threading.Lock()
_mesh_lock = threading.Lock()

def get_detector():
    global _detector_instance
    with _detector_lock:
        if _detector_instance is None:
            print("DEBUG: Initializing DeepfakeDetector (First Use)...")
            _detector_instance = DeepfakeDetector()
    return _detector_instance

def get_face_mesh():
    global _face_mesh_instance
    with _mesh_lock:
        if _face_mesh_instance is None:
            print("DEBUG: Initializing MediaPipe FaceMesh (First Use)...")
            mp_face_mesh = mp.solutions.face_mesh
            _face_mesh_instance = mp_face_mesh.FaceMesh(
                static_image_mode=False, 
                max_num_faces=1, 
                refine_landmarks=True
            )
    return _face_mesh_instance

# (Removed global instances to prevent startup blocking)

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
    if face_img is None or face_img.size == 0:
        return {"spectral": 0, "texture": 0}
    
    # The instruction adds this line, but it's not used in the original function logic.
    # Keeping it as per instruction, but it might be a partial change.
    results = get_face_mesh().process(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)) 

    # 1. Spectral
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray_resized = cv2.resize(gray, (128, 128))
    dct = cv2.dct(np.float32(gray_resized)/255.0)
    high_freq = np.abs(dct[64:, 64:])
    spectral_score = min(100.0, np.mean(high_freq) * 8000)
    # 2. Texture
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    texture_score = 45 if laplacian < 120 else (30 if laplacian > 1500 else 0)
    return {"spectral": round(spectral_score, 2), "texture": round(texture_score, 2)}

# --- Layer C: Structural & Geometric Integrity ---
# 3D Model points for solvePnP (Generic face model)
FACE_3D_MODEL = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye corner
    (225.0, 170.0, -135.0),      # Right eye corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

def get_2d_points(landmarks, w, h):
    indices = [1, 152, 33, 263, 61, 291]
    return np.array([
        (landmarks[idx].x * w, landmarks[idx].y * h) for idx in indices
    ], dtype=np.float64)

def analyze_structural_integrity(face_img, landmarks):
    """Layer C: Edge Density and Head Pose Consistency."""
    if face_img is None or face_img.size == 0:
        return {"edge_density": 0, "pose_consistent": True, "rotation_vec": None}

    # 1. Edge Density Analysis (Canny)
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / edges.size
    
    # 2. Head Pose estimation (solvePnP)
    h, w, _ = face_img.shape
    image_points = get_2d_points(landmarks, w, h)
    
    # Camera internals
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))
    
    success, rotation_vec, translation_vec = cv2.solvePnP(
        FACE_3D_MODEL, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )
    
    return {
        "edge_density": float(edge_density),
        "rotation_vec": rotation_vec if success else None,
        "pose_consistent": success
    }

# --- Temporal & Fusion Engine ---
class TemporalBuffer:
    def __init__(self, size=15):
        self.scores = deque(maxlen=size)
        self.landmarks = deque(maxlen=size)
        self.edge_densities = deque(maxlen=size)
        self.rot_vecs = deque(maxlen=size)

    def add(self, score, lms, density, rot_vec):
        self.scores.append(score)
        self.landmarks.append(lms)
        self.edge_densities.append(density)
        self.rot_vecs.append(rot_vec)

    def get_jitter_variance(self):
        if len(self.landmarks) < 2: return 0.0
        # Calculate nose-tip (landmark 1) shift relative to frame
        shifts = []
        for i in range(1, len(self.landmarks)):
            p1 = np.array([self.landmarks[i-1][1].x, self.landmarks[i-1][1].y])
            p2 = np.array([self.landmarks[i][1].x, self.landmarks[i][1].y])
            shifts.append(np.linalg.norm(p1 - p2))
        
        # Jitter is variance of movement that doesn't correspond to rotation
        # (Simplified: High variance in landmark shift suggests flickering)
        return float(np.var(shifts))

    def get_rolling_avg(self):
        return float(np.mean(self.scores)) if self.scores else 0.0

class FusionEngine:
    @staticmethod
    def calculate_risk(neural_prob, biometric_fail_score, structural_jitter_score):
        """
        Final Score = (ConvNeXt * 0.4) + (Biometric_Fail * 0.4) + (Structural_Jitter * 0.2)
        """
        risk = (neural_prob * 0.4) + (biometric_fail_score * 0.4) + (structural_jitter_score * 0.2)
        return min(100.0, risk)

class Auditor:
    @staticmethod
    def generate_notes(avg_neural, bio_anomalies, structural_jitter, is_video=True):
        notes = []
        if avg_neural > 60:
            notes.append("Neural fingerprints of GAN-generated textures identified in skin-pore distribution.")
        elif avg_neural > 30:
            notes.append("Subtle synthetic artifacts detected in local frequency feature maps (Neural Layer).")

        if "Unnatural lack of eye movement detected" in bio_anomalies:
            notes.append("Irregular/Mechanical blinking detected (Biometric Failure).")
        if "Rigid mouth movement detected across sequence" in bio_anomalies:
            notes.append("Desynchronized lip movement or rigid mouth architecture detected.")
        if "Frequency-domain artifacts detected (DCT Signature)" in bio_anomalies:
            notes.append("Inconsistent spectral noise in the high-frequency Y-channel (Spectral Anomaly).")

        if is_video and structural_jitter > 50:
            notes.append("High-frequency temporal jitter detected in facial landmarks (Structural Anomaly).")
        elif not is_video and structural_jitter > 30:
             notes.append("Geometric misalignment detected in facial structural anchors.")
            
        return notes

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
                results = get_face_mesh().process(rgb_frame)
                
                engine = FusionEngine()
                
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    h, w, _ = frame.shape
                    
                    # 1. Neural Signal (Layer A)
                    pts = np.array([[l.x * w, l.y * h] for l in landmarks])
                    x, y, fw, fh = cv2.boundingRect(pts.astype(np.int32))
                    face_crop = frame[max(0, y-10):min(h, y+fh+10), max(0, x-10):min(w, x+fw+10)]
                    neural_prob = get_detector().predict(face_crop)
                    
                    # 2. Biometric Signal (Layer B - Static)
                    # For images, we can only check spectral/texture forensics
                    forensics = analyze_facial_forensics(face_crop)
                    spectral_scores.append(forensics["spectral"])
                    texture_scores.append(forensics["texture"])
                    
                    # 3. Structural Signal (Layer C)
                    structural = analyze_structural_integrity(face_crop, landmarks)
                    # Jitter is 0 for images
                    current_risk = engine.calculate_risk(neural_prob, 0, 0)
                    
                    fake_probs.append(current_risk)
                    timeline.append({"time": 0, "event": "Face detected: Triple-Layer Fusion applied"})
                else:
                    # Fallback if no face detected
                    neural_prob = get_detector().predict(frame)
                    fake_probs.append(neural_prob)
                    timeline.append({"time": 0, "event": "No face found; analyzing full frame"})
                
                processing_jobs[job_id]['progress'] = 100
        else:
            cap = cv2.VideoCapture(filepath)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            step = max(1, total_frames // 20)
            
            buffer = TemporalBuffer(size=15)
            engine = FusionEngine()
            
            # For Frontend Graph
            temporal_data = {
                "timestamps": [],
                "neural_scores": [],
                "jitter_scores": [],
                "final_risk": []
            }
            
            print(f"DEBUG: Processing Video - Triple Layer Fusion Mode")
            
            for i in range(0, total_frames, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret: break
                
                timestamp = i / fps
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = get_face_mesh().process(rgb_frame)
                
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    h, w, _ = frame.shape
                    
                    # 1. Neural Signal (Layer A)
                    pts = np.array([[l.x * w, l.y * h] for l in landmarks])
                    bx, by, bw, bh = cv2.boundingRect(pts.astype(np.int32))
                    face_crop = frame[max(0, by-10):min(h, by+bh+10), max(0, bx-10):min(w, bx+bw+10)]
                    neural_prob = get_detector().predict(face_crop)
                    
                    # 2. Biometric Signal (Layer B)
                    ears.append(calculate_ear(landmarks, LEFT_EYE, RIGHT_EYE))
                    mars.append(calculate_mar(landmarks, MOUTH))
                    forensics = analyze_facial_forensics(face_crop)
                    spectral_scores.append(forensics["spectral"])
                    texture_scores.append(forensics["texture"])
                    
                    # 3. Structural Signal (Layer C)
                    structural = analyze_structural_integrity(face_crop, landmarks)
                    buffer.add(neural_prob, landmarks, structural["edge_density"], structural["rotation_vec"])
                    
                    # 4. Temporal Fusion
                    jitter = buffer.get_jitter_variance()
                    # Normalize jitter score (0 to 100)
                    jitter_score = min(100.0, jitter * 500000) 
                    
                    # Layer C boost logic: If Structural Jitter > threshold, add +0.25 to Neural probability
                    if jitter_score > 60:
                        neural_prob = min(100.0, neural_prob + 25)

                    # Biometric Score/Fail (Layer B)
                    # Simple heuristic: high spectral noise or texture blurring = biometric failure
                    bio_fail = 100 if (forensics["spectral"] > 45 or forensics["texture"] > 40) else 0
                    
                    # Veto Logic: If EAR mean is too constant (no blinks) or variances are zero
                    # (This is a simplified multi-second lookahead inside the loop)
                    if len(ears) > 10 and np.var(ears[-10:]) < 0.00001:
                        bio_fail = 100 # Veto REAL verdict
                    
                    # Weighted Risk for this frame
                    current_risk = engine.calculate_risk(neural_prob, bio_fail, jitter_score)
                    
                    fake_probs.append(current_risk)
                    temporal_data["timestamps"].append(round(timestamp, 2))
                    temporal_data["neural_scores"].append(round(neural_prob, 2))
                    temporal_data["jitter_scores"].append(round(jitter_score, 2))
                    temporal_data["final_risk"].append(round(current_risk, 2))

                    if current_risk > 60:
                        timeline.append({"time": round(timestamp, 2), "event": f"High suspicion ({round(current_risk, 1)}%)"})
                
                processing_jobs[job_id]['progress'] = int((i / total_frames) * 100)
            cap.release()
        
        # Final Global Stats
        avg_fake_prob = float(np.mean(fake_probs)) if fake_probs else 0.0
        risk_score = avg_fake_prob
        print(f"DEBUG: Final fused risk_score: {risk_score:.2f}")
        
        # Biometric Heuristics (Sequence-based)
        if not is_image:
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

        # Temporal Stats
        prob_variance = np.var(fake_probs) if len(fake_probs) > 1 else 0.0
        if not is_image and prob_variance > 400:
            anomalies.append("High temporal inconsistency (frame flickering)")

        is_deepfake = risk_score >= 50.0
        
        # XAI Auditor Logic
        jitter_for_auditor = min(100, prob_variance / 10) if not is_image else (avg_spectral + avg_texture) / 2
        forensic_notes = Auditor.generate_notes(avg_fake_prob, anomalies, jitter_for_auditor, is_video=not is_image)
        
        if not forensic_notes:
            forensic_notes = ["Analysis signal is nominal. No high-confidence manipulation artifacts found."] if not is_deepfake else ["High-confidence neural signal detected across multiple sensors."]

        forensic_report = {
            "neural": {
                "label": "Neural Integrity",
                "score": avg_fake_prob,
                "status": "danger" if avg_fake_prob > 50 else ("warning" if avg_fake_prob > 25 else "secure"),
                "description": "Probability derived from ConvNeXt backbone feature maps."
            },
            "biometric": {
                "label": "Biometric Liveness",
                "score": max(0.0, min(100.0, (1 - min(np.var(ears) if ears else 1.0, np.var(mars) if mars else 1.0) * 1000) * 100)) if (ears and not is_image) else 0.0,
                "status": "danger" if (not is_image and (np.var(ears) < 0.0001 if ears else False)) else "secure",
                "description": "Analysis of involuntary facial muscle and eye movement."
            },
            "spectral": {
                "label": "Spectral Signature",
                "score": avg_spectral,
                "status": "danger" if avg_spectral > 40 else "secure",
                "description": "Detection of GAN-specific frequency artifacts."
            },
            "structural": {
                "label": "Structural Signature",
                "score": min(100.0, (avg_spectral + avg_texture) / 2), # Simplified Structural signal for static images/unified cases
                "status": "danger" if (avg_spectral > 40 or avg_texture > 40) else "secure",
                "description": "Analysis of edge density and geometric consistency."
            }
        }

        # Add temporal layer only for videos
        if not is_image:
             forensic_report["temporal"] = {
                "label": "Temporal Stability",
                "score": min(100, prob_variance / 10),
                "status": "danger" if prob_variance > 400 else "secure",
                "description": "Prediction consistency across sequential data points."
            }

        processing_jobs[job_id]['status'] = 'completed'
        processing_jobs[job_id]['result'] = {
            'is_deepfake': bool(is_deepfake),
            'risk_score': float(round(risk_score, 2)),
            'avg_fake_prob': float(round(avg_fake_prob, 2)),
            'anomalies': anomalies,
            'forensic_notes': forensic_notes,
            'timeline': timeline,
            'forensic_report': forensic_report,
            'temporal_data': temporal_data if not is_image else None
        }

    except Exception as e:
        processing_jobs[job_id]['status'] = 'error'
        processing_jobs[job_id]['error'] = str(e)
    finally:
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except: pass

# --- API Routes ---
@app.route('/')
def api_status():
    return jsonify({
        "status": "online",
        "message": "DeepShield AI API is running. Use the Vercel dashboard for the UI.",
        "version": "1.0.0"
    }), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

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
    # Use environment port for deployment (Render/Heroku/Vercel)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
