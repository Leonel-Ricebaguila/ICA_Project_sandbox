#!/usr/bin/env python3
"""
Unified Flask server for ICA Project.
Handles both NFC card management and user/camera management with logging.
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

# Add parent directory to path to import unified_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unified_db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ica_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Set database path
DB_PATH = os.environ.get("ICA_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ica_unified.db"))


def log_request(endpoint: str, method: str, data: Optional[Dict] = None, user_id: Optional[int] = None):
    """Log API requests for audit purposes."""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id,
        "data": data,
        "ip": request.remote_addr
    }
    logger.info(f"API Request: {log_data}")


def _parse_role(value: Any) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise ValueError("role must be an integer") from exc


# Health check
@app.get("/health")
def health():
    return jsonify({"status": "ok", "database": DB_PATH})


# User management endpoints
@app.get("/users")
def list_users():
    """List all users."""
    try:
        users = unified_db.list_users(DB_PATH)
        log_request("/users", "GET")
        return jsonify([asdict(u) for u in users])
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/users/<int:user_id>")
def get_user(user_id: int):
    """Get user by ID."""
    try:
        user = unified_db.get_user_by_id(user_id, DB_PATH)
        if not user:
            return jsonify({"error": "User not found"}), 404
        log_request(f"/users/{user_id}", "GET", user_id=user_id)
        return jsonify(asdict(user))
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.post("/users")
def create_user():
    """Create a new user."""
    try:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        nombre = (payload.get("nombre") or "").strip()
        correo = (payload.get("correo") or "").strip()
        rol = (payload.get("rol") or "").strip()
        ip_camara = (payload.get("ip_camara") or "").strip() or None
        
        if not nombre or not correo or not rol:
            return jsonify({"error": "nombre, correo, and rol are required"}), 400
        
        user_id = unified_db.create_user(nombre, correo, rol, ip_camara, DB_PATH)
        log_request("/users", "POST", payload, user_id)
        return jsonify({"status": "created", "user_id": user_id}), 201
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.put("/users/<int:user_id>")
def update_user(user_id: int):
    """Update user information."""
    try:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        nombre = payload.get("nombre")
        correo = payload.get("correo")
        rol = payload.get("rol")
        ip_camara = payload.get("ip_camara")
        
        success = unified_db.update_user(user_id, nombre, correo, rol, ip_camara, DB_PATH)
        if not success:
            return jsonify({"error": "User not found or no changes made"}), 404
        
        log_request(f"/users/{user_id}", "PUT", payload, user_id)
        return jsonify({"status": "updated"})
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.delete("/users/<int:user_id>")
def delete_user(user_id: int):
    """Delete a user and all associated cards."""
    try:
        success = unified_db.delete_user(user_id, DB_PATH)
        if not success:
            return jsonify({"error": "User not found"}), 404
        
        log_request(f"/users/{user_id}", "DELETE", user_id=user_id)
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Camera management endpoints
@app.get("/cameras")
def list_cameras():
    """List all users with their camera information."""
    try:
        users = unified_db.list_users(DB_PATH)
        cameras = []
        for user in users:
            if user.ip_camara:
                cameras.append({
                    "user_id": user.id_usuario,
                    "nombre": user.nombre,
                    "ip_camara": user.ip_camara,
                    "rol": user.rol
                })
        
        log_request("/cameras", "GET")
        return jsonify(cameras)
    except Exception as e:
        logger.error(f"Error listing cameras: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/cameras/<int:user_id>")
def get_camera(user_id: int):
    """Get camera information for a specific user."""
    try:
        user = unified_db.get_user_by_id(user_id, DB_PATH)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.ip_camara:
            return jsonify({"error": "User has no camera configured"}), 404
        
        camera_info = {
            "user_id": user.id_usuario,
            "nombre": user.nombre,
            "ip_camara": user.ip_camara,
            "rol": user.rol
        }
        
        log_request(f"/cameras/{user_id}", "GET", user_id=user_id)
        return jsonify(camera_info)
    except Exception as e:
        logger.error(f"Error getting camera for user {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


# NFC Card management endpoints (existing functionality)
@app.get("/cards")
def list_cards():
    """List all NFC cards."""
    try:
        records = unified_db.list_cards(DB_PATH)
        log_request("/cards", "GET")
        return jsonify([asdict(r) for r in records])
    except Exception as e:
        logger.error(f"Error listing cards: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/cards/<uid>")
def get_card(uid: str):
    """Get card by UID."""
    try:
        record = unified_db.get_card(uid, DB_PATH)
        if not record:
            return jsonify({"error": "Card not found"}), 404
        log_request(f"/cards/{uid}", "GET")
        return jsonify(asdict(record))
    except Exception as e:
        logger.error(f"Error getting card {uid}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.post("/cards")
def upsert_card():
    """Create or update a card."""
    try:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        uid = (payload.get("uid") or "").strip()
        if not uid:
            return jsonify({"error": "uid is required"}), 400
        
        try:
            role = _parse_role(payload.get("role"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        note = (payload.get("note") or "").strip()
        id_usuario = payload.get("id_usuario")  # Optional user association
        
        unified_db.upsert_card(uid=uid, role=role, note=note, id_usuario=id_usuario, db_path=DB_PATH)
        log_request("/cards", "POST", payload)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Error upserting card: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.delete("/cards/<uid>")
def delete_card(uid: str):
    """Delete a card."""
    try:
        removed = unified_db.delete_card(uid, DB_PATH)
        if not removed:
            return jsonify({"error": "Card not found"}), 404
        log_request(f"/cards/{uid}", "DELETE")
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error(f"Error deleting card {uid}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/lookup/<uid>")
def lookup(uid: str):
    """Lookup card access permissions."""
    try:
        record = unified_db.get_card(uid, DB_PATH)
        if not record:
            log_request(f"/lookup/{uid}", "GET")
            return jsonify({"uid": uid, "allowed": False, "role": None})
        
        log_request(f"/lookup/{uid}", "GET")
        return jsonify({"uid": record.uid, "allowed": True, "role": record.role})
    except Exception as e:
        logger.error(f"Error looking up card {uid}: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/users/<int:user_id>/cards")
def get_user_cards(user_id: int):
    """Get all cards for a specific user."""
    try:
        cards = unified_db.get_cards_by_user(user_id, DB_PATH)
        log_request(f"/users/{user_id}/cards", "GET", user_id=user_id)
        return jsonify([asdict(c) for c in cards])
    except Exception as e:
        logger.error(f"Error getting cards for user {user_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Logging endpoints for camera system
@app.post("/log")
def log_event():
    """Log events from camera system and other clients."""
    try:
        payload = request.get_json(silent=True) or {}
        event_type = payload.get("event_type", "unknown")
        user_id = payload.get("user_id")
        user_name = payload.get("user_name", "unknown")
        data = payload.get("data", {})
        
        # Log the event
        log_message = f"CAMERA_EVENT - Type: {event_type}, User: {user_name} (ID: {user_id})"
        if data:
            log_message += f", Data: {data}"
        
        logger.info(log_message)
        
        # Store in database for persistence (optional)
        # You could create a logs table if needed
        
        return jsonify({"status": "logged"})
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        return jsonify({"error": "Failed to log event"}), 500


@app.get("/logs")
def get_recent_logs():
    """Get recent log entries (for debugging/monitoring)."""
    try:
        # This is a simple implementation - in production you might want to use a proper logging database
        return jsonify({
            "message": "Logs are written to ica_server.log file",
            "log_file": "ica_server.log"
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Face detection statistics endpoint
@app.get("/face-detection/stats")
def get_face_detection_stats():
    """Get face detection statistics."""
    try:
        # This would typically come from a database or file
        # For now, return a placeholder response
        return jsonify({
            "message": "Face detection statistics would be available here",
            "note": "Statistics are logged to the server log file"
        })
    except Exception as e:
        logger.error(f"Error getting face detection stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


def main():
    """Main function to run the server."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    
    # Initialize database
    unified_db.initialize_database(DB_PATH)
    
    logger.info(f"Starting ICA Unified Server on {host}:{port}")
    logger.info(f"Database: {DB_PATH}")
    
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    main()
