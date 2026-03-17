import os
import cv2
import torch
import torch.nn as nn
import numpy as np
import gradio as gr
from PIL import Image
import mediapipe as mp
# Robust submodule imports to bypass __init__ issues on specific platforms
try:
    import mediapipe.solutions.face_mesh as mp_face_mesh
    print(f"DEBUG: MediaPipe FaceMesh loaded directly. Version: {mp.__version__}")
except ImportError:
    try:
        from mediapipe.python.solutions import face_mesh as mp_face_mesh
        print("DEBUG: MediaPipe FaceMesh loaded via python.solutions.")
    except ImportError:
        import mediapipe.solutions.face_mesh as mp_face_mesh
        print("DEBUG: MediaPipe FaceMesh loaded via standard solutions path.")
        
from collections import deque
from huggingface_hub import hf_hub_download

# --- ConvNeXt Model Architecture ---
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
        self.model.to(self.device).eval()
        
        # Hugging Face Weights Loading - CRITICAL: Strip any hidden newlines/spaces
        repo_id = os.environ.get('HF_REPO_ID', '').strip()
        filename = os.environ.get('HF_FILENAME', 'convnext_video_fixed.pth').strip()
        
        # Log cleaned ID for debugging (mask for safety)
        if repo_id:
            print(f"DEBUG: Using HF_REPO_ID: {repo_id[:4]}...{repo_id[-4:] if len(repo_id) > 8 else ''}")
        else:
            print("DEBUG: No HF_REPO_ID found in environment.")
        
        weights_path = None
        if os.path.exists(filename): weights_path = filename
        elif repo_id:
            try:
                print(f"DEBUG: Downloading weights from {repo_id}...")
                weights_path = hf_hub_download(repo_id=repo_id, filename=filename)
            except Exception as e:
                print(f"HF Download Failed: {e}")

        if weights_path:
            state_dict = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            print("DEBUG: Model weights loaded successfully.")
        else:
            print("WARNING: Model weights NOT FOUND. Using random initialization.")

    def predict(self, face_img):
        if face_img is None or face_img.size == 0: return 0.0
        yuv = cv2.cvtColor(face_img, cv2.COLOR_BGR2YUV)
        yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
        face_img = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        
        img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img_rgb, (224, 224))
        img = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406], device=self.device).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=self.device).view(3, 1, 1)
        img = (img - mean) / std
        img = img.unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(img)
            prob = torch.softmax(output, dim=1)[0, 1].item() * 100
        return float(prob)

# --- Forensics & XAI Logic ---
def analyze_facial_forensics(face_img):
    if face_img is None or face_img.size == 0: return {"spectral": 0, "texture": 0}
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray_resized = cv2.resize(gray, (128, 128))
    dct = cv2.dct(np.float32(gray_resized)/255.0)
    high_freq = np.abs(dct[64:, 64:])
    spectral_score = min(100.0, np.mean(high_freq) * 8000)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
    texture_score = 45 if laplacian < 120 else (30 if laplacian > 1500 else 0)
    return {"spectral": round(spectral_score, 2), "texture": round(texture_score, 2)}

def analyze_structural_integrity(face_img, landmarks):
    if face_img is None or face_img.size == 0: return {"edge_density": 0}
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return {"edge_density": float(np.sum(edges > 0) / edges.size)}

class Auditor:
    def generate_notes(self, neural, anomalies, jitter, is_video=True):
        notes = []
        if neural > 60: notes.append("Neural fingerprints of GAN-generated textures identified.")
        if "Frequency-domain artifacts detected (DCT Signature)" in anomalies:
            notes.append("Inconsistent spectral noise in the high-frequency Y-channel.")
        if not is_video and jitter > 30: notes.append("Geometric misalignment detected in facial structural anchors.")
        return notes

# --- Main App Logic ---
try:
    face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True)
except Exception as e:
    print(f"DEBUG: FaceMesh initialization failed: {e}")
    # Final fallback attempt
    import mediapipe.solutions.face_mesh as fm
    face_mesh = fm.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True)

detector = DeepfakeDetector()
auditor = Auditor()

def process_media(input_file):
    if input_file is None: return "No file uploaded", None, None
    is_video = input_file.endswith(('.mp4', '.avi', '.mov', '.mkv'))
    
    if is_video:
        cap = cv2.VideoCapture(input_file)
        ret, frame = cap.read()
        cap.release()
        if not ret: return "Video error", None, None
    else:
        frame = cv2.imread(input_file)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    if not results.multi_face_landmarks: return "No face detected.", None, None

    landmarks = results.multi_face_landmarks[0].landmark
    h, w, _ = frame.shape
    pts = np.array([[l.x * w, l.y * h] for l in landmarks])
    x, y, fw, fh = cv2.boundingRect(pts.astype(np.int32))
    face_crop = frame[max(0, y-10):min(h, y+fh+10), max(0, x-10):min(w, x+fw+10)]
    
    neural_prob = detector.predict(face_crop)
    forensics = analyze_facial_forensics(face_crop)
    
    anomalies = []
    if forensics["spectral"] > 40: anomalies.append("Frequency-domain artifacts detected (DCT Signature)")
    notes = auditor.generate_notes(neural_prob, anomalies, forensics["spectral"], is_video=is_video)
    
    risk = (neural_prob * 0.6) + (forensics["spectral"] * 0.4)
    verdict = "FAKE/MANIPULATED" if risk > 50 else "REAL/AUTHENTIC"
    
    output_text = f"## Verdict: {verdict}\n### Confidence: {risk:.2f}%\n\n**Forensic Notes:**\n" + "\n".join([f"- {n}" for n in notes])
    return output_text, Image.fromarray(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)), {"Neural": neural_prob/100, "Forensic": forensics["spectral"]/100}

# --- Gradio UI ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="cyan")) as demo:
    gr.Markdown("# 🛡️ DeepShield AI: Unified Forensic Detector")
    with gr.Row():
        with gr.Column():
            input_media = gr.File(label="Upload Media")
            btn = gr.Button("🔍 Run Analysis", variant="primary")
        with gr.Column():
            res_md = gr.Markdown("Analysis results will appear here...")
            prev_img = gr.Image(label="Face Analysis")
            label_out = gr.Label(label="Signals")
    btn.click(process_media, inputs=input_media, outputs=[res_md, prev_img, label_out])

if __name__ == "__main__":
    demo.launch()
