#!/usr/bin/env python3
"""
Unified camera monitoring system for ICA Project.
Uses the unified server API instead of direct database access.
"""

import cv2
import requests
import json
import logging
from typing import List, Dict, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration
SERVER_BASE_URL = "http://localhost:8080"  # Change this to your server URL


class CameraManager:
    """Manages camera connections and video streams."""
    
    def __init__(self, server_url: str = SERVER_BASE_URL):
        self.server_url = server_url
        self.caps = []  # Array of video streams
        self.camera_info = []  # Array of camera information
        self.window_width = 320
        self.window_height = 240
    
    def get_cameras_from_server(self) -> List[Dict]:
        """Fetch camera information from the server."""
        try:
            response = requests.get(f"{self.server_url}/cameras", timeout=5)
            response.raise_for_status()
            cameras = response.json()
            logger.info(f"Retrieved {len(cameras)} cameras from server")
            return cameras
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching cameras from server: {e}")
            return []
    
    def get_camera_by_user_id(self, user_id: int) -> Optional[Dict]:
        """Get camera information for a specific user."""
        try:
            response = requests.get(f"{self.server_url}/cameras/{user_id}", timeout=5)
            if response.status_code == 404:
                logger.warning(f"Camera not found for user {user_id}")
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching camera for user {user_id}: {e}")
            return None
    
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
            cap = cv2.VideoCapture(ip_camara)
            if not cap.isOpened():
                print(f"Error: No se pudo conectar a la cámara de {nombre}")
                continue
            
            self.caps.append(cap)
            self.camera_info.append(camera_info)
            print(f"✓ Conectado exitosamente a {nombre}")
        
        return len(self.caps) > 0
    
    def display_video_streams(self):
        """Display video streams from all connected cameras."""
        if not self.caps:
            print("No hay cámaras conectadas")
            return
        
        print("Presiona ESC para salir")
        print("Presiona 's' para tomar screenshot")
        
        while True:
            for i, cap in enumerate(self.caps):
                ret, frame = cap.read()
                if not ret:
                    print(f"Error al obtener video de la cámara {self.camera_info[i]['nombre']}")
                    continue
                
                # Create window and resize frame
                window_name = f"Camara de {self.camera_info[i]['nombre']}"
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                frame = cv2.resize(frame, (self.window_width, self.window_height))
                
                # Add user info overlay
                info_text = f"{self.camera_info[i]['nombre']} ({self.camera_info[i]['rol']})"
                cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow(window_name, frame)
            
            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                break
            elif key == ord('s'):  # Screenshot
                self.take_screenshot()
    
    def take_screenshot(self):
        """Take screenshots of all active camera streams."""
        timestamp = cv2.getTickCount()
        for i, cap in enumerate(self.caps):
            ret, frame = cap.read()
            if ret:
                filename = f"screenshot_{self.camera_info[i]['nombre']}_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Screenshot guardado: {filename}")
    
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
    """Main function to access cameras through the server API."""
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
        
        # Initialize camera manager and connect
        camera_manager = CameraManager()
        if not camera_manager.connect_to_cameras(selected_user_ids):
            print("No se pudo conectar a ninguna cámara")
            return
        
        # Display video streams
        camera_manager.display_video_streams()
        
        # Cleanup
        camera_manager.release_cameras()
        
    except Exception as e:
        logger.error(f"Error in acceder(): {e}")
        print(f"Ocurrió un error: {e}")


def main():
    """Main entry point."""
    print("=== ICA Camera Monitoring System (Unified) ===")
    print(f"Conectando al servidor: {SERVER_BASE_URL}")
    
    while True:
        print("\nOpciones:")
        print("1. Acceder a cámaras")
        print("2. Listar cámaras disponibles")
        print("3. Salir")
        
        choice = input("Seleccione una opción: ").strip()
        
        if choice == "1":
            acceder()
        elif choice == "2":
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

