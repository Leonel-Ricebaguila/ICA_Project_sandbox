#!/usr/bin/env python3
"""
Enhanced camera monitoring system with face detection for ICA Project.
Uses OpenCV pre-trained models for face detection and the unified server API.
"""

# ============================================================================
# IMPORTS AND DEPENDENCIES
# ============================================================================
# Computer vision and image processing
import cv2
import numpy as np

# HTTP requests for server communication
import requests
import json

# Data handling and analysis
import pandas as pd
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Logging for debugging and monitoring
import logging

# ============================================================================
# CONFIGURATION AND SETUP
# ============================================================================
# Setup logging system for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration - API endpoint for camera data
SERVER_BASE_URL = "http://localhost:8080"  # Change this to your server URL


# ============================================================================
# FACE DETECTION CLASS
# ============================================================================
class FaceDetector:
    """
    Face detection using OpenCV pre-trained models.
    Handles face, eye, and smile detection with data logging capabilities.
    """
    
    def __init__(self):
        # ====================================================================
        # INITIALIZE DETECTION MODELS
        # ====================================================================
        # Haar Cascade classifiers for different facial features
        self.face_cascade = None      # Main face detection classifier
        self.eye_cascade = None      # Eye detection within faces
        self.smile_cascade = None    # Smile detection within faces
        
        # Advanced DNN-based face detection (optional, more accurate)
        self.face_detector = None    # Deep neural network face detector
        self.face_recognizer = None  # Face recognition (not implemented yet)
        
        # ====================================================================
        # DATA COLLECTION AND ANALYTICS
        # ====================================================================
        # DataFrame to store face detection statistics and logs
        self.face_data = pd.DataFrame(columns=[
            'timestamp',    # When detection occurred
            'user_id',      # ID of the user whose camera detected faces
            'user_name',    # Name of the user
            'face_count',   # Number of faces detected
            'confidence'    # Detection confidence score
        ])
        
        # Load all face detection models
        self._load_models()
    
    def _load_models(self):
        """
        Load OpenCV pre-trained models for face detection.
        Tries DNN models first (more accurate), falls back to Haar cascades.
        """
        try:
            # ====================================================================
            # LOAD HAAR CASCADE CLASSIFIERS (PRIMARY METHOD)
            # ====================================================================
            # These are fast, lightweight pre-trained models included with OpenCV
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
            
            # ====================================================================
            # ATTEMPT TO LOAD DNN-BASED FACE DETECTION (MORE ACCURATE)
            # ====================================================================
            try:
                # Try to load DNN face detection model (requires external model files)
                model_path = "opencv_face_detector_uint8.pb"
                config_path = "opencv_face_detector.pbtxt"
                
                # Check if DNN model files exist
                if not (cv2.os.path.exists(model_path) and cv2.os.path.exists(config_path)):
                    logger.warning("DNN face detection models not found, using Haar cascades")
                    self.face_detector = None
                else:
                    # Load DNN model for more accurate face detection
                    self.face_detector = cv2.dnn.readNetFromTensorflow(model_path, config_path)
                    logger.info("DNN face detection model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load DNN model: {e}, using Haar cascades")
                self.face_detector = None
            
            logger.info("Face detection models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading face detection models: {e}")
            raise
    
    def detect_faces_haar(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using Haar cascade classifier.
        Fast and lightweight method for real-time face detection.
        
        Args:
            frame: Input image frame (BGR format)
            
        Returns:
            List of face rectangles as (x, y, width, height) tuples
        """
        # Convert to grayscale for faster processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces using Haar cascade with optimized parameters
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,      # How much the image size is reduced at each scale
            minNeighbors=5,       # Minimum neighbors required for a detection
            minSize=(30, 30),     # Minimum face size to detect
            flags=cv2.CASCADE_SCALE_IMAGE  # Use image scaling for better detection
        )
        return faces
    
    def detect_faces_dnn(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces using DNN-based detection (more accurate).
        Uses deep neural network for higher precision face detection.
        
        Args:
            frame: Input image frame (BGR format)
            
        Returns:
            List of face rectangles as (x, y, width, height) tuples
        """
        # Check if DNN model is available
        if self.face_detector is None:
            return []
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Create blob from image for DNN processing
        # Parameters: image, scale factor, input size, mean subtraction values
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123])
        
        # Set input and run detection
        self.face_detector.setInput(blob)
        detections = self.face_detector.forward()
        
        # Process detection results
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:  # Confidence threshold for face detection
                # Extract bounding box coordinates
                x1 = int(detections[0, 0, i, 3] * w)
                y1 = int(detections[0, 0, i, 4] * h)
                x2 = int(detections[0, 0, i, 5] * w)
                y2 = int(detections[0, 0, i, 6] * h)
                # Convert to (x, y, width, height) format
                faces.append((x1, y1, x2-x1, y2-y1))
        
        return faces
    
    def detect_faces(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], float]:
        """
        Detect faces using the best available method.
        Prioritizes DNN for accuracy, falls back to Haar cascades.
        
        Args:
            frame: Input image frame (BGR format)
            
        Returns:
            Tuple of (faces_list, confidence_score)
        """
        # Try DNN first (more accurate but requires model files)
        if self.face_detector is not None:
            faces = self.detect_faces_dnn(frame)
            confidence = 0.8  # DNN confidence score
        else:
            # Fallback to Haar cascades (always available)
            faces = self.detect_faces_haar(frame)
            confidence = 0.6  # Haar cascade confidence score
        
        return faces, confidence
    
    def detect_eyes(self, frame: np.ndarray, face_roi: Tuple[int, int, int, int]) -> List[Tuple[int, int, int, int]]:
        """
        Detect eyes within a face region.
        Searches for eyes only within the detected face area for efficiency.
        
        Args:
            frame: Full image frame
            face_roi: Face region of interest as (x, y, width, height)
            
        Returns:
            List of eye rectangles as (x, y, width, height) tuples
        """
        x, y, w, h = face_roi
        # Extract face region and convert to grayscale
        face_gray = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
        
        # Detect eyes within the face region
        eyes = self.eye_cascade.detectMultiScale(face_gray, 1.1, 3)
        
        # Adjust coordinates back to full frame coordinates
        eyes_adjusted = [(x + ex, y + ey, ew, eh) for ex, ey, ew, eh in eyes]
        return eyes_adjusted
    
    def detect_smiles(self, frame: np.ndarray, face_roi: Tuple[int, int, int, int]) -> List[Tuple[int, int, int, int]]:
        """
        Detect smiles within a face region.
        Searches for smiles only within the detected face area for efficiency.
        
        Args:
            frame: Full image frame
            face_roi: Face region of interest as (x, y, width, height)
            
        Returns:
            List of smile rectangles as (x, y, width, height) tuples
        """
        x, y, w, h = face_roi
        # Extract face region and convert to grayscale
        face_gray = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
        
        # Detect smiles within the face region with relaxed parameters
        smiles = self.smile_cascade.detectMultiScale(face_gray, 1.8, 20)
        
        # Adjust coordinates back to full frame coordinates
        smiles_adjusted = [(x + sx, y + sy, sw, sh) for sx, sy, sw, sh in smiles]
        return smiles_adjusted
    
    def draw_face_annotations(self, frame: np.ndarray, faces: List[Tuple[int, int, int, int]], 
                            user_name: str, user_role: str) -> np.ndarray:
        """
        Draw face detection annotations on the frame.
        Adds bounding boxes, labels, and feature detection overlays.
        
        Args:
            frame: Input video frame
            faces: List of detected face rectangles
            user_name: Name of the camera user
            user_role: Role of the camera user
            
        Returns:
            Annotated frame with detection overlays
        """
        # Create a copy to avoid modifying the original frame
        annotated_frame = frame.copy()
        
        # ====================================================================
        # DRAW FACE DETECTIONS AND FEATURES
        # ====================================================================
        for i, (x, y, w, h) in enumerate(faces):
            # Draw face rectangle (green)
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw face label
            face_label = f"Face {i+1}"
            cv2.putText(annotated_frame, face_label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Detect and draw eyes (blue rectangles)
            eyes = self.detect_eyes(frame, (x, y, w, h))
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(annotated_frame, (ex, ey), (ex + ew, ey + eh), (255, 0, 0), 1)
                cv2.putText(annotated_frame, "Eye", (ex, ey - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # Detect and draw smiles (red rectangles)
            smiles = self.detect_smiles(frame, (x, y, w, h))
            for (sx, sy, sw, sh) in smiles:
                cv2.rectangle(annotated_frame, (sx, sy), (sx + sw, sy + sh), (0, 0, 255), 1)
                cv2.putText(annotated_frame, "Smile", (sx, sy - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # ====================================================================
        # ADD STATUS INFORMATION OVERLAY
        # ====================================================================
        # Add face count info
        face_count_text = f"Faces detected: {len(faces)}"
        cv2.putText(annotated_frame, face_count_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return annotated_frame
    
    def log_face_detection(self, user_id: int, user_name: str, face_count: int, confidence: float):
        """
        Log face detection data to pandas DataFrame.
        Stores detection events for analytics and CSV export.
        
        Args:
            user_id: ID of the user whose camera detected faces
            user_name: Name of the user
            face_count: Number of faces detected
            confidence: Detection confidence score
        """
        timestamp = datetime.now()
        
        # Create new detection record
        new_data = {
            'timestamp': timestamp,
            'user_id': user_id,
            'user_name': user_name,
            'face_count': face_count,
            'confidence': confidence
        }
        
        # Add to DataFrame for analytics
        self.face_data = pd.concat([self.face_data, pd.DataFrame([new_data])], ignore_index=True)
        
        # Log to console for real-time monitoring
        logger.info(f"Face detection - User: {user_name}, Faces: {face_count}, Confidence: {confidence:.2f}")
    
    def get_face_statistics(self) -> Dict:
        """
        Get face detection statistics.
        Calculates comprehensive analytics from collected detection data.
        
        Returns:
            Dictionary containing detection statistics and analytics
        """
        # Return empty stats if no data collected
        if self.face_data.empty:
            return {"total_detections": 0, "unique_users": 0, "avg_faces_per_detection": 0}
        
        # Calculate comprehensive statistics
        stats = {
            "total_detections": len(self.face_data),                    # Total detection events
            "unique_users": self.face_data['user_id'].nunique(),        # Number of different users
            "avg_faces_per_detection": self.face_data['face_count'].mean(),  # Average faces per event
            "total_faces_detected": self.face_data['face_count'].sum(), # Total faces detected
            "avg_confidence": self.face_data['confidence'].mean(),     # Average confidence score
            "detection_by_user": self.face_data.groupby('user_name')['face_count'].sum().to_dict()  # Faces per user
        }
        
        return stats
    
    def save_face_data(self, filename: str = None):
        """
        Save face detection data to CSV file.
        Exports collected detection data for external analysis.
        
        Args:
            filename: Optional custom filename, defaults to timestamp-based name
        """
        # Generate timestamp-based filename if none provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"face_detection_data_{timestamp}.csv"
        
        # Save DataFrame to CSV file
        self.face_data.to_csv(filename, index=False)
        logger.info(f"Face detection data saved to {filename}")


# ============================================================================
# ENHANCED CAMERA MANAGER CLASS
# ============================================================================
class EnhancedCameraManager:
    """
    Enhanced camera manager with face detection capabilities.
    Manages multiple camera streams with real-time face detection and logging.
    """
    
    def __init__(self, server_url: str = SERVER_BASE_URL):
        # ====================================================================
        # SERVER CONFIGURATION
        # ====================================================================
        self.server_url = server_url
        
        # ====================================================================
        # CAMERA STREAM MANAGEMENT
        # ====================================================================
        self.caps = []          # Array of OpenCV VideoCapture objects
        self.camera_info = []   # Array of camera metadata from server
        
        # ====================================================================
        # DISPLAY CONFIGURATION
        # ====================================================================
        self.window_width = 640   # Increased for better face detection
        self.window_height = 480
        
        # ====================================================================
        # FACE DETECTION AND LOGGING
        # ====================================================================
        self.face_detector = FaceDetector()    # Face detection engine
        self.detection_enabled = True          # Toggle face detection on/off
        self.log_to_server_enabled = True     # Toggle server logging on/off
    
    def get_cameras_from_server(self) -> List[Dict]:
        """
        Fetch camera information from the server.
        Retrieves list of all available cameras with their configurations.
        
        Returns:
            List of camera dictionaries with user info and IP addresses
        """
        try:
            # Request camera list from server API
            response = requests.get(f"{self.server_url}/cameras", timeout=5)
            response.raise_for_status()
            cameras = response.json()
            logger.info(f"Retrieved {len(cameras)} cameras from server")
            return cameras
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching cameras from server: {e}")
            return []
    
    def get_camera_by_user_id(self, user_id: int) -> Optional[Dict]:
        """
        Get camera information for a specific user.
        Retrieves camera configuration for a single user by their ID.
        
        Args:
            user_id: ID of the user whose camera info to retrieve
            
        Returns:
            Camera dictionary with user info and IP address, or None if not found
        """
        try:
            # Request specific camera info from server API
            response = requests.get(f"{self.server_url}/cameras/{user_id}", timeout=5)
            if response.status_code == 404:
                logger.warning(f"Camera not found for user {user_id}")
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching camera for user {user_id}: {e}")
            return None
    
    def log_to_server(self, event_type: str, user_id: int, user_name: str, data: Dict):
        """
        Log events to the server for centralized logging.
        Sends detection events and system events to the server API.
        
        Args:
            event_type: Type of event (e.g., 'face_detected', 'camera_connected')
            user_id: ID of the user associated with the event
            user_name: Name of the user
            data: Additional event data dictionary
        """
        # Skip logging if disabled
        if not self.log_to_server_enabled:
            return
        
        try:
            # Prepare log data structure
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "user_name": user_name,
                "data": data
            }
            
            # Send log data to server API
            response = requests.post(f"{self.server_url}/log", json=log_data, timeout=2)
            if response.status_code == 200:
                logger.debug(f"Event logged to server: {event_type}")
            else:
                logger.warning(f"Failed to log event to server: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not log to server: {e}")
    
    def connect_to_cameras(self, user_ids: List[int]) -> bool:
        """Connect to cameras for the specified user IDs."""
        self.caps = []
        self.camera_info = []
        
        for user_id in user_ids:
            camera_info = self.get_camera_by_user_id(user_id)
            if not camera_info:
                print(f"Error: No camera found for user ID {user_id}")
                continue
            
            nombre = camera_info['nombre']
            ip_camara = camera_info['ip_camara']
            
            print(f"Conectando a la cámara de {nombre} en {ip_camara}...")
            
            # Open video stream
            print(f"Intentando conectar a {ip_camara}...")
            cap = cv2.VideoCapture(ip_camara)
            
            # For RTSP streams, set additional properties
            if ip_camara.startswith('rtsp://'):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FPS, 30)
            
            if not cap.isOpened():
                print(f"Error: No se pudo conectar a la cámara de {nombre}")
                print(f"Verifique que la URL {ip_camara} sea correcta y accesible")
                continue
            
            # Test if we can actually read a frame
            ret, test_frame = cap.read()
            if not ret:
                print(f"Error: No se pudo leer frames de la cámara de {nombre}")
                cap.release()
                continue
            
            self.caps.append(cap)
            self.camera_info.append(camera_info)
            print(f"[OK] Conectado exitosamente a {nombre}")
            
            # Log connection to server
            self.log_to_server("camera_connected", user_id, nombre, {
                "camera_ip": ip_camara,
                "connection_time": datetime.now().isoformat()
            })
        
        return len(self.caps) > 0
    
    def display_video_streams(self):
        """
        Display video streams from all connected cameras with face detection.
        Main video processing loop with real-time face detection and user controls.
        """
        # Check if cameras are connected
        if not self.caps:
            print("No hay cámaras conectadas")
            return
        
        # ====================================================================
        # USER CONTROLS INFORMATION
        # ====================================================================
        print("Presiona ESC para salir")
        print("Presiona 's' para tomar screenshot")
        print("Presiona 'f' para toggle face detection")
        print("Presiona 'd' para mostrar estadísticas de detección")
        
        # ====================================================================
        # VIDEO PROCESSING CONFIGURATION
        # ====================================================================
        frame_count = 0
        detection_interval = 60  # Detect faces every 60 frames (performance optimization)
        
        # ====================================================================
        # MAIN VIDEO PROCESSING LOOP
        # ====================================================================
        while True:
            # Process each connected camera
            for i, cap in enumerate(self.caps):
                # Read frame from camera
                ret, frame = cap.read()
                if not ret:
                    print(f"Error al obtener video de la cámara {self.camera_info[i]['nombre']}")
                    
                    # ============================================================
                    # RTSP RECONNECTION LOGIC
                    # ============================================================
                    # For RTSP streams, try to reconnect automatically
                    if self.camera_info[i]['ip_camara'].startswith('rtsp://'):
                        print(f"Intentando reconectar a {self.camera_info[i]['nombre']}...")
                        cap.release()
                        new_cap = cv2.VideoCapture(self.camera_info[i]['ip_camara'])
                        # Configure RTSP stream properties
                        if self.camera_info[i]['ip_camara'].startswith('rtsp://'):
                            new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            new_cap.set(cv2.CAP_PROP_FPS, 30)
                        if new_cap.isOpened():
                            self.caps[i] = new_cap
                            print(f"[OK] Reconectado exitosamente a {self.camera_info[i]['nombre']}")
                        else:
                            print(f"No se pudo reconectar a {self.camera_info[i]['nombre']}")
                    continue
                
                # ============================================================
                # FRAME PROCESSING
                # ============================================================
                # Resize frame for consistent display and better performance
                frame = cv2.resize(frame, (self.window_width, self.window_height))
                
                # ============================================================
                # FACE DETECTION PROCESSING
                # ============================================================
                # Perform face detection periodically (not every frame for performance)
                if self.detection_enabled and frame_count % detection_interval == 0:
                    faces, confidence = self.face_detector.detect_faces(frame)
                    
                    # Process detected faces
                    if len(faces) > 0:
                        # ========================================================
                        # LOG FACE DETECTION DATA
                        # ========================================================
                        # Log to local DataFrame for analytics
                        self.face_detector.log_face_detection(
                            self.camera_info[i]['user_id'],
                            self.camera_info[i]['nombre'],
                            len(faces),
                            confidence
                        )
                        
                        # Log to server for centralized monitoring
                        self.log_to_server("face_detected", 
                                         self.camera_info[i]['user_id'],
                                         self.camera_info[i]['nombre'],
                                         {
                                             "face_count": len(faces),
                                             "confidence": confidence,
                                             "frame_number": frame_count
                                         })
                        
                        # Draw face annotations
                        frame = self.face_detector.draw_face_annotations(
                            frame, faces, 
                            self.camera_info[i]['nombre'], 
                            self.camera_info[i]['rol']
                        )
                    else:
                        # Draw user info even when no faces detected
                        info_text = f"{self.camera_info[i]['nombre']} ({self.camera_info[i]['rol']})"
                        cv2.putText(frame, info_text, (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, "No faces detected", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                else:
                    # Draw user info
                    info_text = f"{self.camera_info[i]['nombre']} ({self.camera_info[i]['rol']})"
                    cv2.putText(frame, info_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    if not self.detection_enabled:
                        cv2.putText(frame, "Face detection: OFF", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                
                # Create window and display
                window_name = f"Camara de {self.camera_info[i]['nombre']}"
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.imshow(window_name, frame)
            
            frame_count += 1
            
            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                break
            elif key == ord('s'):  # Screenshot
                self.take_screenshot()
            elif key == ord('f'):  # Toggle face detection
                self.detection_enabled = not self.detection_enabled
                status = "ON" if self.detection_enabled else "OFF"
                print(f"Face detection {status}")
            elif key == ord('d'):  # Show detection statistics
                self.show_detection_statistics()
    
    def take_screenshot(self):
        """Take screenshots of all active camera streams."""
        timestamp = cv2.getTickCount()
        for i, cap in enumerate(self.caps):
            ret, frame = cap.read()
            if ret:
                filename = f"screenshot_{self.camera_info[i]['nombre']}_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Screenshot guardado: {filename}")
                
                # Log screenshot to server
                self.log_to_server("screenshot_taken", 
                                 self.camera_info[i]['user_id'],
                                 self.camera_info[i]['nombre'],
                                 {"filename": filename})
    
    def show_detection_statistics(self):
        """Display face detection statistics."""
        stats = self.face_detector.get_face_statistics()
        print("\n=== Face Detection Statistics ===")
        print(f"Total detections: {stats['total_detections']}")
        print(f"Unique users: {stats['unique_users']}")
        print(f"Average faces per detection: {stats['avg_faces_per_detection']:.2f}")
        print(f"Total faces detected: {stats['total_faces_detected']}")
        print(f"Average confidence: {stats['avg_confidence']:.2f}")
        print("\nDetections by user:")
        for user, count in stats['detection_by_user'].items():
            print(f"  {user}: {count} faces")
        print("===============================\n")
    
    def save_detection_data(self):
        """Save face detection data to CSV."""
        self.face_detector.save_face_data()
        print("Face detection data saved to CSV file")
    
    def release_cameras(self):
        """Release all camera connections."""
        for cap in self.caps:
            cap.release()
        cv2.destroyAllWindows()
        logger.info("All cameras released")


def list_available_cameras(server_url: str = SERVER_BASE_URL) -> List[Dict]:
    """List all available cameras from the server."""
    try:
        response = requests.get(f"{server_url}/cameras", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching cameras: {e}")
        return []


def acceder():
    """Main function to access cameras through the server API with face detection."""
    try:
        # Check server connectivity
        try:
            response = requests.get(f"{SERVER_BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                print("Error: Servidor no disponible")
                return
        except requests.exceptions.RequestException:
            print("Error: No se puede conectar al servidor")
            return
        
        # List available cameras
        cameras = list_available_cameras()
        if not cameras:
            print("No hay cámaras disponibles en el servidor")
            return
        
        print("Cámaras disponibles:")
        for i, cam in enumerate(cameras):
            print(f"{i+1}. {cam['nombre']} (ID: {cam['user_id']}) - {cam['ip_camara']}")
        
        # Get user input for camera selection
        try:
            num_cameras = int(input("\nIngrese el número de cámaras a usar: "))
            if num_cameras <= 0 or num_cameras > len(cameras):
                print("Número inválido de cámaras")
                return
        except ValueError:
            print("Por favor ingrese un número válido")
            return
        
        selected_user_ids = []
        for i in range(num_cameras):
            try:
                user_id = int(input(f"Ingrese el ID de usuario para la cámara {i+1}: "))
                # Verify user exists and has camera
                if any(cam['user_id'] == user_id for cam in cameras):
                    selected_user_ids.append(user_id)
                else:
                    print(f"Usuario {user_id} no encontrado o sin cámara")
            except ValueError:
                print("Por favor ingrese un ID de usuario válido")
                continue
        
        if not selected_user_ids:
            print("No se seleccionaron usuarios válidos")
            return
        
        # Initialize enhanced camera manager and connect
        camera_manager = EnhancedCameraManager()
        if not camera_manager.connect_to_cameras(selected_user_ids):
            print("No se pudo conectar a ninguna cámara")
            return
        
        # Display video streams with face detection
        camera_manager.display_video_streams()
        
        # Save detection data before cleanup
        camera_manager.save_detection_data()
        
        # Cleanup
        camera_manager.release_cameras()
        
    except Exception as e:
        logger.error(f"Error in acceder(): {e}")
        print(f"Ocurrió un error: {e}")


# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================
def main():
    """
    Main entry point for the ICA Camera Monitoring System with Face Detection.
    Provides interactive menu for camera access and system management.
    """
    print("=== ICA Camera Monitoring System with Face Detection ===")
    print(f"Conectando al servidor: {SERVER_BASE_URL}")
    
    # ====================================================================
    # INTERACTIVE MENU LOOP
    # ====================================================================
    while True:
        print("\nOpciones:")
        print("1. Acceder a cámaras con detección facial")
        print("2. Listar cámaras disponibles")
        print("3. Salir")
        
        choice = input("Seleccione una opción: ").strip()
        
        if choice == "1":
            # Launch face detection camera system
            acceder()
        elif choice == "2":
            # List available cameras from server
            cameras = list_available_cameras()
            if cameras:
                print("\nCámaras disponibles:")
                for cam in cameras:
                    print(f"- {cam['nombre']} (ID: {cam['user_id']}) - {cam['ip_camara']}")
            else:
                print("No hay cámaras disponibles")
        elif choice == "3":
            print("Saliendo...")
            break
        else:
            print("Opción inválida")


if __name__ == "__main__":
    main()
