# Deepfake Detection System

A Real-Time Video Deepfake Detection Pipeline processing frames through a custom `convnext_video.pth` PyTorch model and MediaPipe behavioral analysis.

## Features
- **Live Tracking**: Analyzes webcam feed every 500ms.
- **Neural Confidence**: Uses `convnext_video.pth` to predict if the frame is a deepfake.
- **Biometric Analysis**: Uses MediaPipe to check Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR) for blink and lip-sync anomalies.
- **Squid Game Aesthetic**: High-tech Security Monitor HUD.

## Setup Instructions

### 1. Linking your Model
Ensure your trained model, `convnext_video.pth`, is placed at the root of the project:
```
hackaton/
├── convnext_video.pth  <-- Place your model here
├── backend/
└── frontend/
```
*Note: If your `.pth` file is just a `state_dict`, you will need to add the `ConvNeXt` model class definition inside `backend/app.py` before loading it.*

### 2. Backend (Flask)
1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python app.py
   ```
The backend will run on `http://localhost:5000`.

### 3. Frontend (React)
1. Open a new terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open the provided local URL (usually `http://localhost:5173`) in your browser and allow webcam access.
