import os
# Force the backend libraries to stay silent in the terminal for a clean boot
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['GLOG_minloglevel'] = '2'

import cv2
import mediapipe as mp
import numpy as np
import threading
import queue
import time
import math
import random
from collections import deque
from scipy.spatial import distance as dist

# ---------------------------------------------------------
# 1. AUDIO ENGINE (Threaded macOS Native)
# ---------------------------------------------------------
audio_queue = queue.Queue()

def audio_worker():
    """Runs in the background to handle macOS 'say' without freezing the camera feed."""
    while True:
        task = audio_queue.get()
        if task is None:
            break
        role, warning_type = task
        if warning_type == "wake":
            os.system(f"say 'Warning! {role} is falling asleep!'")
        elif warning_type == "distract":
            os.system(f"say '{role}, look forward!'")
        audio_queue.task_done()

# Start the audio thread immediately
audio_thread = threading.Thread(target=audio_worker, daemon=True)
audio_thread.start()

# ---------------------------------------------------------
# 2. CONFIGURATION & SAFETY THRESHOLDS
# ---------------------------------------------------------
EAR_THRESHOLD = 0.23        
MAR_THRESHOLD = 0.65        
PITCH_THRESHOLD = -15.0      # Head downward tilt (Nodding off)
YAW_THRESHOLD = 20.0         # Head sideways tilt (Distraction/Looking away)
DROWSY_TIME_THRESH = 1.5   
DISTRACTION_TIME_THRESH = 1.5 
MAX_PEOPLE = 2               # STRICTLY 2 PEOPLE (Driver & Passenger)

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
LIPS = [61, 291, 13, 14]

# ---------------------------------------------------------
# 3. LOGGING & MATH UTILITIES
# ---------------------------------------------------------
system_logs = deque(maxlen=6)

def log_event(msg):
    timestamp = time.strftime("%H:%M:%S")
    system_logs.append(f"[{timestamp}] {msg}")

def calculate_ear(eye_pts):
    A = dist.euclidean(eye_pts[1], eye_pts[5])
    B = dist.euclidean(eye_pts[2], eye_pts[4])
    C = dist.euclidean(eye_pts[0], eye_pts[3])
    if C == 0: return 0.0
    return (A + B) / (2.0 * C)

def calculate_mar(lip_pts):
    A = dist.euclidean(lip_pts[2], lip_pts[3]) 
    B = dist.euclidean(lip_pts[0], lip_pts[1]) 
    if B == 0: return 0.0
    return A / B

def get_head_pose(shape, img_w, img_h):
    model_points = np.array([
        (0.0, 0.0, 0.0),             
        (0.0, -330.0, -65.0),        
        (-225.0, 170.0, -135.0),     
        (225.0, 170.0, -135.0),      
        (-150.0, -150.0, -125.0),    
        (150.0, -150.0, -125.0)      
    ], dtype=np.float64)

    image_points = np.array([
        shape[1], shape[152], shape[33], shape[263], shape[61], shape[291]    
    ], dtype=np.float64)

    focal_length = img_w
    center = (img_w / 2, img_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4, 1))
    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success: return 0.0, 0.0, 0.0

    rotation_mat, _ = cv2.Rodrigues(rotation_vector)
    pose_mat = cv2.hconcat((rotation_mat, translation_vector))
    _, _, _, _, _, _, euler_angle = cv2.decomposeProjectionMatrix(pose_mat)

    return euler_angle[0, 0], euler_angle[1, 0], euler_angle[2, 0]

def draw_smart_bounds(frame, x, y, w, h, color):
    thickness = 2
    length = 25
    cv2.line(frame, (x, y), (x + length, y), color, thickness)
    cv2.line(frame, (x, y), (x, y + length), color, thickness)
    cv2.line(frame, (x + w, y), (x + w - length, y), color, thickness)
    cv2.line(frame, (x + w, y), (x + w, y + length), color, thickness)
    cv2.line(frame, (x, y + h), (x + length, y + h), color, thickness)
    cv2.line(frame, (x, y + h), (x, y + h - length), color, thickness)
    cv2.line(frame, (x + w, y + h), (x + w - length, y + h), color, thickness)
    cv2.line(frame, (x + w, y + h), (x + w, y + h - length), color, thickness)

# ---------------------------------------------------------
# 4. CYBER-BOOT ANIMATION SCREEN
# ---------------------------------------------------------
def show_boot_screen():
    width, height = 960, 540
    window_name = "System Boot Sequence"
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, width, height)
    
    if os.path.exists("engine.mp3"):
        os.system("afplay engine.mp3 &") 
    else:
        os.system("say -v Samantha 'Driver drowsiness detection program is starting. Sensors online.' &")

    boot_logs = []
    fake_processes = [
        "INITIALIZING CAMERA FEED...", 
        "MOUNTING DEEP NEURAL MESH...", 
        "CALIBRATING IR/CLAHE NIGHT VISION...", 
        "ENGAGING MULTI-VECTOR TELEMETRY (EAR/MAR/3D-POSE)...", 
        "INITIALIZING DYNAMIC TARGET TRACKING...",
        "ACTIVATING PRIORITY AUDIO QUEUE...",
        "ALL SYSTEMS NOMINAL. ENGAGING."
    ]
    
    steps = 150
    matrix_columns = width // 20
    drops = [random.randint(-50, height) for _ in range(matrix_columns)]
    
    for i in range(steps + 1):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        for j in range(matrix_columns):
            char = chr(random.randint(33, 126))
            cv2.putText(frame, char, (j * 20, drops[j]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, random.randint(50, 150), 0), 1)
            drops[j] += random.randint(10, 20)
            if drops[j] > height or random.random() > 0.95:
                drops[j] = random.randint(-50, 0)
                
        center = (250, 270)
        cv2.line(frame, (center[0]-160, center[1]), (center[0]-180, center[1]), (0, 255, 255), 2)
        cv2.line(frame, (center[0]+160, center[1]), (center[0]+180, center[1]), (0, 255, 255), 2)
        cv2.line(frame, (center[0], center[1]-160), (center[0], center[1]-180), (0, 255, 255), 2)
        cv2.line(frame, (center[0], center[1]+160), (center[0], center[1]+180), (0, 255, 255), 2)
        
        t = i * 0.1
        cv2.ellipse(frame, center, (140, 140), math.degrees(t * 1.5), 0, 120, (0, 255, 255), 3)   
        cv2.ellipse(frame, center, (125, 125), math.degrees(-t * 2.0), 45, 220, (255, 50, 255), 2)  
        cv2.ellipse(frame, center, (110, 110), math.degrees(t * 3.0), 180, 270, (0, 150, 255), 4)   
        
        pulse = int(abs(math.sin(t * 2)) * 40)
        cv2.circle(frame, center, 30 + pulse, (0, 200, 0), -1)
        cv2.circle(frame, center, 30 + pulse, (200, 255, 200), 2)
        
        sweep_x = int(center[0] + 140 * math.cos(t * 2.5))
        sweep_y = int(center[1] + 140 * math.sin(t * 2.5))
        cv2.line(frame, center, (sweep_x, sweep_y), (0, 255, 0), 2)
        
        hex_data = f"MEM_ADDR: 0x{random.randint(100000, 999999):X}"
        cv2.putText(frame, hex_data, (center[0]-60, center[1]+10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)
        
        wave_box_x, wave_box_y = 480, 70
        cv2.rectangle(frame, (wave_box_x, wave_box_y), (wave_box_x + 400, wave_box_y + 90), (40, 40, 40), 1)
        cv2.putText(frame, "BIOMETRIC CALIBRATION", (wave_box_x, wave_box_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        pts1, pts2 = [], []
        for wx in range(0, 400, 5):
            wy1 = int(45 + math.sin((wx + i * 15) * 0.05) * 20 + math.cos((wx + i * 10) * 0.1) * 10)
            wy2 = int(45 + math.cos((wx - i * 12) * 0.04) * 15 + math.sin((wx - i * 8) * 0.08) * 5)
            pts1.append((wave_box_x + wx, wave_box_y + wy1))
            pts2.append((wave_box_x + wx, wave_box_y + wy2))
            
        for p in range(len(pts1)-1):
            cv2.line(frame, pts1[p], pts1[p+1], (0, 255, 100), 2) 
            cv2.line(frame, pts2[p], pts2[p+1], (255, 0, 100), 1) 

        cv2.putText(frame, "SMART CABIN", (480, 220), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, "TELEMETRY SYSTEM", (480, 260), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(frame, "AI Engine v5.0 Active", (485, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)
        
        if i % 21 == 0 and len(fake_processes) > 0:
            boot_logs.append(fake_processes.pop(0))
            
        for idx, log in enumerate(boot_logs[-5:]): 
            cv2.putText(frame, f"> {log}", (485, 330 + (idx * 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        
        bar_width = 400
        bar_height = 15
        start_x = 485
        start_y = 460
        
        cv2.rectangle(frame, (start_x, start_y), (start_x + bar_width, start_y + bar_height), (50, 50, 50), 2)
        fill_width = int((i / steps) * bar_width)
        cv2.rectangle(frame, (start_x, start_y), (start_x + fill_width, start_y + bar_height), (0, 255, 255), -1)
        cv2.putText(frame, f"BOOTING KERNEL: {int((i/steps)*100)}%", (start_x, start_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        if random.random() < 0.12: 
            g_y = random.randint(0, height - 40)
            g_h = random.randint(15, 40)
            shift = random.randint(-25, 25)
            
            b, g, r = cv2.split(frame[g_y:g_y+g_h, :])
            if shift > 0:
                r[:, shift:] = r[:, :-shift]
                b[:, :-shift] = b[:, shift:]
            elif shift < 0:
                r[:, :shift] = r[:, -shift:]
                b[:, -shift:] = b[:, :shift]
                
            frame[g_y:g_y+g_h, :] = cv2.merge((b, g, r))
            cv2.line(frame, (0, g_y + g_h//2), (width, g_y + g_h//2), (255, 255, 255), 1)

        if i > steps - 6:
            frame = cv2.addWeighted(frame, 0.5, np.full((height, width, 3), 255, dtype=np.uint8), 0.5, 0)
            
        cv2.imshow(window_name, frame)
        cv2.waitKey(25) 
        
    cv2.destroyWindow(window_name)

# ---------------------------------------------------------
# 5. MAIN TRACKING EXECUTION
# ---------------------------------------------------------
def main():
    show_boot_screen()
    
    cap = cv2.VideoCapture(0)
    
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=MAX_PEOPLE,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    
    # Trackers dedicated directly to roles
    timers = {
        "DRIVER": {"drowsy": None, "distract": None, "last_seen": time.time(), "status": "STABLE"},
        "PASSENGER": {"drowsy": None, "distract": None, "last_seen": time.time(), "status": "STABLE"}
    }
    
    known_roles = set()
    last_audio_time = 0
    
    log_event("SYSTEM ONLINE")
    log_event("AWAITING OCCUPANTS...")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
            
        # Flip frame so physical right is screen right
        frame = cv2.flip(frame, 1)
        img_h, img_w = frame.shape[:2]
        
        # CLAHE Night Vision
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        # Draw Background HUD overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (330, img_h), (10, 15, 20), -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)
        
        cv2.putText(frame, "DRIVER TELEMETRY DASHBOARD", (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.50, (255, 255, 255), 1)
        cv2.line(frame, (20, 45), (310, 45), (100, 100, 100), 1)
        cv2.putText(frame, "[SYS] MULTI-VECTOR TELEMETRY: ACTIVE", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        cv2.putText(frame, "[SYS] PRIORITY AUDIO QUEUE: ACTIVE", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        cv2.line(frame, (20, 95), (310, 95), (100, 100, 100), 1)
        
        dial_center = (280, 25)
        angle = time.time() * 3
        end_x = int(dial_center[0] + 8 * math.cos(angle))
        end_y = int(dial_center[1] + 8 * math.sin(angle))
        cv2.circle(frame, dial_center, 10, (100, 100, 100), 1)
        cv2.line(frame, dial_center, (end_x, end_y), (0, 255, 0), 2)
        
        current_time = time.time()
        active_roles_this_frame = set()
        
        # Priority Tracking States
        driver_needs_alarm = False
        driver_warning_type = ""
        passenger_needs_alarm = False
        passenger_warning_type = ""
        
        if results.multi_face_landmarks:
            faces_with_x = []
            for face_landmarks in results.multi_face_landmarks:
                shape = [(int(pt.x * img_w), int(pt.y * img_h)) for pt in face_landmarks.landmark]
                x_coords = [pt[0] for pt in shape]
                y_coords = [pt[1] for pt in shape]
                x_min, x_max = max(0, min(x_coords) - 20), min(img_w, max(x_coords) + 20)
                y_min, y_max = max(0, min(y_coords) - 20), min(img_h, max(y_coords) + 20)
                
                # Filter out background false positives
                if (x_max - x_min) < 50 or (y_max - y_min) < 50:
                    continue
                
                nose_x = shape[1][0]
                faces_with_x.append((nose_x, face_landmarks, shape, x_min, x_max, y_min, y_max))
                
            # Sort Left to Right based on X coord
            faces_with_x.sort(key=lambda item: item[0])
            
            # Map faces to Driver and Passenger roles
            current_targets = {}
            if len(faces_with_x) == 2:
                current_targets["PASSENGER"] = faces_with_x[0] # Left side
                current_targets["DRIVER"] = faces_with_x[1]    # Right side
            elif len(faces_with_x) == 1:
                # If only one person, decide based on screen half
                if faces_with_x[0][0] > img_w / 2:
                    current_targets["DRIVER"] = faces_with_x[0]
                else:
                    current_targets["PASSENGER"] = faces_with_x[0]

            for role, data in current_targets.items():
                _, face_landmarks, shape, x_min, x_max, y_min, y_max = data
                
                active_roles_this_frame.add(role)
                timers[role]["last_seen"] = current_time
                
                if role not in known_roles:
                    known_roles.add(role)
                    log_event(f"ROLE IDENTIFIED: {role}")
                
                # Biological Mask Rendering
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                
                left_ear = calculate_ear([shape[i] for i in LEFT_EYE])
                right_ear = calculate_ear([shape[i] for i in RIGHT_EYE])
                ear = max(left_ear, right_ear)
                mar = calculate_mar([shape[i] for i in LIPS])
                pitch, yaw, roll = get_head_pose(shape, img_w, img_h)
                
                status = "STABLE"
                ui_color = (0, 255, 0)
                risk_pct = 0
                
                eyes_closed = (ear < EAR_THRESHOLD)
                head_nodded = (pitch < PITCH_THRESHOLD)
                is_distracted = (abs(yaw) > YAW_THRESHOLD)
                
                # --- FATIGUE EVALUATION ---
                if eyes_closed:
                    timers[role]["distract"] = None 
                    risk_pct = min(100, int(((EAR_THRESHOLD - ear) / EAR_THRESHOLD) * 400))

                    if timers[role]["drowsy"] is None:
                        timers[role]["drowsy"] = current_time
                        if head_nodded: log_event(f"{role} NODDING OFF")
                        else: log_event(f"{role} EYES DROPPING")
                            
                    elif current_time - timers[role]["drowsy"] >= DROWSY_TIME_THRESH:
                        status = "CRITICAL"
                        ui_color = (0, 0, 255) 
                        risk_pct = 100
                        if role == "DRIVER":
                            driver_needs_alarm = True
                            driver_warning_type = "wake"
                        else:
                            passenger_needs_alarm = True
                            passenger_warning_type = "wake"
                            
                        if (current_time * 10) % 10 < 1: 
                            log_event(f"{role} FATIGUE ALARM!")
                            
                # --- DISTRACTION EVALUATION ---
                elif is_distracted:
                    timers[role]["drowsy"] = None 
                    risk_pct = min(100, int((abs(yaw) / 45.0) * 100)) 
                    
                    if timers[role]["distract"] is None:
                        timers[role]["distract"] = current_time
                        
                    elif current_time - timers[role]["distract"] >= DISTRACTION_TIME_THRESH:
                        status = "DISTRACTED"
                        ui_color = (0, 165, 255) 
                        
                        if role == "DRIVER":
                            driver_needs_alarm = True
                            driver_warning_type = "distract"
                        else:
                            passenger_needs_alarm = True
                            passenger_warning_type = "distract"
                            
                        if (current_time * 10) % 10 < 1:
                            log_event(f"{role} DISTRACTION WARNING!")
                            
                else:
                    timers[role]["drowsy"] = None
                    timers[role]["distract"] = None
                    if mar > MAR_THRESHOLD:
                        status = "YAWNING"
                        ui_color = (255, 255, 0) 
                        if (current_time * 10) % 10 < 1: log_event(f"{role} YAWNING")

                timers[role]["status"] = status
                
                # Box overlay around face
                draw_smart_bounds(frame, x_min, y_min, x_max - x_min, y_max - y_min, ui_color)
                nose_x, nose_y = shape[4]
                cv2.drawMarker(frame, (nose_x, nose_y), ui_color, cv2.MARKER_CROSS, 15, 1)

                cv2.putText(frame, f"ROLE: {role}", (x_max + 10, y_min + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ui_color, 1)
                cv2.putText(frame, f"STS: {status}", (x_max + 10, y_min + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ui_color, 1)
                
                # Dedicated HUD Locations
                hud_y = 120 if role == "DRIVER" else 220
                cv2.putText(frame, f"TARGET: {role}", (20, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(frame, f"[{status}]", (160, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ui_color, 1)
                
                cv2.putText(frame, f"EAR: {ear:.3f} | YAW: {yaw:.1f}deg", (20, hud_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(frame, f"RISK LEVEL:", (20, hud_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                bar_width = 150
                fill_width = int((risk_pct / 100) * bar_width)
                cv2.rectangle(frame, (130, hud_y + 36), (130 + bar_width, hud_y + 44), (50, 50, 50), -1) 
                cv2.rectangle(frame, (130, hud_y + 36), (130 + fill_width, hud_y + 44), ui_color, -1) 
                
        else:
            cv2.putText(frame, "NO FACES DETECTED", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # --- AUTO CLEANUP / DISTRACTION FALLBACK ---
        for role in list(known_roles):
            if role not in active_roles_this_frame:
                time_missing = current_time - timers[role]["last_seen"]
                
                if DISTRACTION_TIME_THRESH <= time_missing < 4.0:
                    if role == "DRIVER":
                        driver_needs_alarm = True; driver_warning_type = "distract"
                    else:
                        passenger_needs_alarm = True; passenger_warning_type = "distract"
                    
                    hud_y = 120 if role == "DRIVER" else 220
                    cv2.putText(frame, f"TARGET: {role}", (20, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(frame, "[FACE LOST]", (160, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                    cv2.putText(frame, "EXTREME DISTRACTION", (20, hud_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
                    
                    if (current_time * 10) % 10 < 1: log_event(f"{role} FACE LOST ALARM!")
                        
                elif time_missing >= 4.0:
                    known_roles.remove(role)
                    timers[role]["drowsy"] = None
                    timers[role]["distract"] = None
                    log_event(f"AUTO-CLEANUP: {role} CLEARED")

        # --- PRIORITY AUDIO EXECUTION ---
        # 3.0 second cooldown prevents overlapping text-to-speech spam
        if current_time - last_audio_time > 3.0:
            if driver_needs_alarm:
                audio_queue.put(("Driver", driver_warning_type))
                last_audio_time = current_time
            elif passenger_needs_alarm:
                audio_queue.put(("Passenger", passenger_warning_type))
                last_audio_time = current_time

        # --- EVENT LOG RENDERING ---
        log_y_start = img_h - 130
        cv2.putText(frame, "SYSTEM EVENT LOG", (20, log_y_start), cv2.FONT_HERSHEY_DUPLEX, 0.5, (100, 100, 255), 1)
        cv2.line(frame, (20, log_y_start + 10), (310, log_y_start + 10), (50, 50, 100), 1)
        for i, log_msg in enumerate(system_logs):
            y_pos = log_y_start + 30 + (i * 15)
            cv2.putText(frame, log_msg, (20, y_pos), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (0, 255, 0), 1)

        # Flash entire screen red if DRIVER is critical
        if timers["DRIVER"]["status"] == "CRITICAL" or driver_needs_alarm:
            pulse_intensity = int(abs(math.sin(time.time() * 8)) * 255)
            cv2.rectangle(frame, (0, 0), (img_w, img_h), (0, 0, pulse_intensity), 8)
            cv2.putText(frame, "CRITICAL ALERT", (350, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, pulse_intensity), 2)

        cv2.imshow("Smart Cabin Telemetry Sys", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
            
    cap.release()
    cv2.destroyAllWindows()
    audio_queue.put(None) 
    audio_thread.join()

if __name__ == "__main__":
    main()