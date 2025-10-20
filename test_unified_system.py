#!/usr/bin/env python3
"""
Test script for the unified ICA system.
Tests database migration, server functionality, and camera API.
"""

import requests
import json
import time
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import unified_db

SERVER_URL = "http://localhost:8080"
DB_PATH = "ica_unified.db"


def test_database():
    """Test database functionality."""
    print("=== Testing Database ===")
    
    # Test user operations
    print("Testing user operations...")
    
    # Create a test user
    import time
    unique_email = f"test_{int(time.time())}@example.com"
    user_id = unified_db.create_user("Test User", unique_email, "Test Role", "http://test.com/video", DB_PATH)
    print(f"[OK] Created user with ID: {user_id}")
    
    # Get user
    user = unified_db.get_user_by_id(user_id, DB_PATH)
    print(f"[OK] Retrieved user: {user.nombre}")
    
    # Update user
    unified_db.update_user(user_id, ip_camara="http://updated.com/video", db_path=DB_PATH)
    updated_user = unified_db.get_user_by_id(user_id, DB_PATH)
    print(f"[OK] Updated user camera: {updated_user.ip_camara}")
    
    # Test card operations
    print("Testing card operations...")
    
    # Create a test card
    unified_db.upsert_card("TEST123", 1, "Test card", user_id, DB_PATH)
    print("[OK] Created test card")
    
    # Get card
    card = unified_db.get_card("TEST123", DB_PATH)
    print(f"[OK] Retrieved card: {card.uid}")
    
    # Cleanup
    unified_db.delete_card("TEST123", DB_PATH)
    unified_db.delete_user(user_id, DB_PATH)
    print("[OK] Cleaned up test data")
    
    print("Database tests passed!\n")


def test_server():
    """Test server API endpoints."""
    print("=== Testing Server API ===")
    
    # Test health endpoint
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Server health check passed")
        else:
            print("[FAIL] Server health check failed")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Cannot connect to server: {e}")
        return False
    
    # Test users endpoint
    try:
        response = requests.get(f"{SERVER_URL}/users", timeout=5)
        if response.status_code == 200:
            users = response.json()
            print(f"[OK] Retrieved {len(users)} users")
        else:
            print("[FAIL] Failed to retrieve users")
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Error retrieving users: {e}")
    
    # Test cameras endpoint
    try:
        response = requests.get(f"{SERVER_URL}/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json()
            print(f"[OK] Retrieved {len(cameras)} cameras")
        else:
            print("[FAIL] Failed to retrieve cameras")
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Error retrieving cameras: {e}")
    
    # Test cards endpoint
    try:
        response = requests.get(f"{SERVER_URL}/cards", timeout=5)
        if response.status_code == 200:
            cards = response.json()
            print(f"[OK] Retrieved {len(cards)} cards")
        else:
            print("[FAIL] Failed to retrieve cards")
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Error retrieving cards: {e}")
    
    print("Server API tests completed!\n")
    return True


def test_camera_api():
    """Test camera-specific API endpoints."""
    print("=== Testing Camera API ===")
    
    # Get available cameras
    try:
        response = requests.get(f"{SERVER_URL}/cameras", timeout=5)
        if response.status_code == 200:
            cameras = response.json()
            print(f"[OK] Found {len(cameras)} available cameras")
            
            for cam in cameras:
                print(f"  - {cam['nombre']} (ID: {cam['user_id']}) - {cam['ip_camara']}")
                
                # Test individual camera endpoint
                try:
                    cam_response = requests.get(f"{SERVER_URL}/cameras/{cam['user_id']}", timeout=5)
                    if cam_response.status_code == 200:
                        print(f"    [OK] Camera {cam['nombre']} endpoint working")
                    else:
                        print(f"    [FAIL] Camera {cam['nombre']} endpoint failed")
                except requests.exceptions.RequestException as e:
                    print(f"    [FAIL] Error testing camera {cam['nombre']}: {e}")
        else:
            print("[FAIL] Failed to retrieve cameras")
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Error retrieving cameras: {e}")
    
    print("Camera API tests completed!\n")


def main():
    """Run all tests."""
    print("ICA Unified System Test Suite")
    print("=" * 40)
    
    # Test database
    test_database()
    
    # Test server (if running)
    print("Note: Make sure the server is running before testing API endpoints")
    print("Start server with: python NFC_ServerSide/server_unified.py")
    
    server_running = test_server()
    
    if server_running:
        test_camera_api()
    
    print("Test suite completed!")
    print("\nTo start the system:")
    print("1. Start server: python NFC_ServerSide/server_unified.py")
    print("2. Run camera client: python camaras_unified.py")


if __name__ == "__main__":
    main()
