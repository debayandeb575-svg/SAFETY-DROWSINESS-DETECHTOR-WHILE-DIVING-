# SAFETY-DROWSINESS-DETECHTOR-WHILE-DIVING-# 🚗 Smart Cabin Telemetry System - Driver Drowsiness & Distraction Detection

> Real-time Driver & Passenger monitoring system with Cyber Boot Animation, CLAHE Night Vision, and Multi-Vector Telemetry.

This project detects **Drowsiness (Eye Closure), Yawning (MAR), Head Nodding (Pitch), and Distraction (Yaw)** for 2 people simultaneously using MediaPipe Face Mesh 468 landmarks.

### Video Demo
`Press 'q' to quit | Cyber boot animation on startup`

---

### ✨ Key Features

**1. Dual Role Tracking (Driver & Passenger)**
- Left side of frame = PASSENGER
- Right side of frame = DRIVER
- Automatic role identification and auto-cleanup if person leaves frame for >4s

**2. Multi-Vector Biometric Analysis**
- `EAR (Eye Aspect Ratio)` - Detects eyes closing
- `MAR (Mouth Aspect Ratio)` - Detects yawning
- `3D Head Pose (Pitch, Yaw, Roll)` - Detects nodding off and looking away using `cv2.solvePnP`
- `Face Lost Detection` - Triggers "EXTREME DISTRACTION" if face disappears

**3. Cyber Boot Sequence**
- Matrix rain background
- Orbital rings animation
- Biometric wave calibration
- Glitch effects and boot logs

**4. HUD & Safety System**
- CLAHE Night Vision for low-light
- Smart bounding boxes with corner markers
- Risk level bars (Green -> Orange -> Red)
- System Event Log with timestamps
- Threaded macOS Audio Engine (`say` command) - Non-blocking warnings
- Critical Alert red screen flash for Driver

---

### 🛠️ Tech Stack

- Python 3.11 (Required for `mp.solutions`)
- OpenCV (cv2) - Camera, CLAHE, solvePnP
- MediaPipe - Face Mesh 468 landmarks
- SciPy - Euclidean distance for EAR/MAR
- Threading + Queue - For audio

---

### 📁 Project Structure
