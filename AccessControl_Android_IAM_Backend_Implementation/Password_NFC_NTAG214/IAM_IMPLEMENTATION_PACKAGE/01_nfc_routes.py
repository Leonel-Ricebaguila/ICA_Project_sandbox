"""
NFC Device & Scanning API Routes
Handles Android NFC app integration for IAM_Backend

This file provides endpoints for:
- Device authentication (JWT tokens)
- NFC card scanning (access control)
- Device heartbeat (monitoring)
- Device information retrieval
- NFC card assignment (admin)
- Server configuration

Created: October 26, 2025
For: UPY Sentinel NFC Android App Integration
"""

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Usuario, NFCDevice, Evento
from ..time_utils import now_cst
import datetime
import hashlib
import secrets
import jwt
import os

bp = Blueprint("nfc", __name__, url_prefix="/api")

# ========== CONFIGURATION ==========

# JWT Configuration - Get from environment or use defaults
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.environ.get('NFC_DEVICE_JWT_EXP_SECONDS', '86400'))  # 24 hours default

# ========== DATABASE CONTEXT MANAGER ==========

class DB:
    """Database session context manager"""
    def __enter__(self):
        self.db: Session = SessionLocal()
        return self.db
    
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
        self.db.close()


# ========== HELPER FUNCTIONS ==========

def verify_device_token():
    """
    Verify JWT token from Authorization header
    Returns: (device_id, error_response) - error_response is None if valid
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Unauthorized - Bearer token required"}), 401)
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        device_id = payload.get("device_id")
        
        if not device_id:
            return None, (jsonify({"error": "Invalid token - device_id missing"}), 401)
        
        return device_id, None
        
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token expired"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Invalid token"}), 401)


# ========== DEVICE AUTHENTICATION ==========

@bp.post("/nfc_devices/auth")
def nfc_device_auth():
    """
    Authenticate NFC device and return JWT token
    
    Request Body:
    {
        "device_id": "NFC-READER-001",
        "device_secret": "base64_secret",
        "location": "Main Entrance",
        "android_version": "13",
        "app_version": "1.0.0"
    }
    
    Response:
    {
        "token": "jwt_token_here",
        "expires_at": 1698342000,
        "device_info": {...}
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get("device_id", "").strip()
    device_secret = data.get("device_secret", "").strip()
    location = data.get("location", "")
    
    if not device_id or not device_secret:
        return jsonify({"error": "device_id and device_secret required"}), 400
    
    with DB() as db:
        # Find device by device_id
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            return jsonify({"error": "Device not registered"}), 401
        
        # Verify device secret
        if device.device_secret != device_secret:
            return jsonify({"error": "Invalid device secret"}), 401
        
        # Check device status
        if device.status != "active":
            return jsonify({"error": f"Device status is '{device.status}', must be 'active'"}), 403
        
        # Update device information
        device.last_seen = now_cst()
        device.ip = request.remote_addr
        
        if "android_version" in data:
            device.android_version = data["android_version"]
        if "app_version" in data:
            device.app_version = data["app_version"]
        if location:
            device.location = location
        
        # Generate JWT token
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION)
        token_payload = {
            "device_id": device_id,
            "device_db_id": device.id,
            "type": "nfc_device",
            "location": device.location or location,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.datetime.utcnow().timestamp())
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        # Log authentication event
        event = Evento(
            event="nfc_device_authenticated",
            actor_uid=None,
            source=device_id,
            context={
                "device_name": device.name,
                "ip": request.remote_addr,
                "android_version": device.android_version,
                "app_version": device.app_version
            }
        )
        db.add(event)
        
        return jsonify({
            "token": token,
            "expires_at": int(expires_at.timestamp()),
            "device_info": {
                "id": device.id,
                "name": device.name,
                "status": device.status,
                "location": device.location or location,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            }
        })


# ========== NFC SCANNING ==========

@bp.post("/nfc/scan")
def nfc_scan():
    """
    Process NFC card scan and grant/deny access
    
    Request Body:
    {
        "nfc_uid": "04A3B2C1D4E5F6",
        "nfc_uid_hash": "sha256_hash",
        "device_id": "NFC-READER-001",
        "timestamp": "2025-10-26T15:30:00Z",
        "location": "Main Entrance",
        "card_type": "Mifare Classic"
    }
    
    Response (Granted):
    {
        "result": "granted",
        "user": {...},
        "access_level": "standard",
        "message": "Access granted",
        "event_id": 12345,
        "timestamp": "..."
    }
    
    Response (Denied):
    {
        "result": "denied",
        "reason": "card_not_registered",
        "message": "...",
        "timestamp": "..."
    }
    """
    # Verify JWT token
    device_id, error = verify_device_token()
    if error:
        return error
    
    # Get scan data
    data = request.get_json(force=True, silent=True) or {}
    nfc_uid = data.get("nfc_uid", "").strip()
    nfc_uid_hash = data.get("nfc_uid_hash", "")
    location = data.get("location", "")
    card_type = data.get("card_type")
    
    if not nfc_uid:
        return jsonify({
            "result": "denied",
            "reason": "invalid_request",
            "message": "nfc_uid required",
            "timestamp": now_cst().isoformat()
        }), 400
    
    with DB() as db:
        # Verify device is still active
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device or device.status != "active":
            return jsonify({
                "result": "denied",
                "reason": "device_inactive",
                "message": "Device not active",
                "timestamp": now_cst().isoformat()
            }), 403
        
        # Update device last_seen
        device.last_seen = now_cst()
        
        # Lookup user by NFC UID
        user = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        
        # Try hash lookup if direct UID not found
        if not user and nfc_uid_hash:
            user = db.query(Usuario).filter(Usuario.nfc_uid_hash == nfc_uid_hash).first()
        
        # CASE 1: Card not registered
        if not user:
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=None,
                source=device_id,
                context={
                    "nfc_uid_truncated": nfc_uid[-4:] if len(nfc_uid) >= 4 else nfc_uid,
                    "reason": "card_not_registered",
                    "location": location,
                    "card_type": card_type
                }
            )
            db.add(event)
            
            return jsonify({
                "result": "denied",
                "reason": "card_not_registered",
                "message": "NFC card not associated with any user",
                "timestamp": now_cst().isoformat()
            })
        
        # CASE 2: User account inactive
        if user.estado != "active":
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=user.uid,
                source=device_id,
                context={
                    "reason": "user_inactive",
                    "user_estado": user.estado,
                    "location": location
                }
            )
            db.add(event)
            
            return jsonify({
                "result": "denied",
                "reason": "user_inactive",
                "message": f"User account is {user.estado}",
                "timestamp": now_cst().isoformat()
            })
        
        # CASE 3: NFC card status not active
        if user.nfc_status != "active":
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=user.uid,
                source=device_id,
                context={
                    "reason": "card_revoked",
                    "nfc_status": user.nfc_status,
                    "location": location
                }
            )
            db.add(event)
            
            return jsonify({
                "result": "denied",
                "reason": "card_revoked",
                "message": f"NFC card status: {user.nfc_status}",
                "timestamp": now_cst().isoformat()
            })
        
        # CASE 4: ACCESS GRANTED ✅
        
        # Update user last access
        user.ultimo_acceso = now_cst()
        
        # Log success event
        event = Evento(
            event="nfc_scan_granted",
            actor_uid=user.uid,
            source=device_id,
            context={
                "location": location,
                "card_type": card_type,
                "device_name": device.name,
                "user_rol": user.rol
            }
        )
        db.add(event)
        db.flush()  # Get event ID
        
        # Determine access level based on role (can be enhanced)
        access_level_map = {
            "R-ADMIN": "admin",
            "R-IAM": "admin",
            "R-SEC": "security",
            "R-AUD": "auditor",
            "R-EMP": "standard",
            "R-CEO": "executive",
            "R-VIS": "visitor"
        }
        access_level = access_level_map.get(user.rol, "standard")
        
        return jsonify({
            "result": "granted",
            "user": {
                "uid": user.uid,
                "nombre": user.nombre,
                "apellido": user.apellido,
                "rol": user.rol,
                "foto_url": f"/static/avatars/{user.uid}.png",
                "email": user.email
            },
            "access_level": access_level,
            "message": "Access granted",
            "event_id": event.id,
            "timestamp": now_cst().isoformat()
        })


# ========== BATCH SCAN (Offline Sync) ==========

@bp.post("/nfc/scan/batch")
def nfc_scan_batch():
    """
    Process multiple NFC scans (offline sync)
    
    Request Body:
    {
        "device_id": "NFC-READER-001",
        "scans": [
            {
                "nfc_uid": "04A3B2C1D4E5F6",
                "timestamp": "2025-10-26T15:25:00Z",
                "location": "Main Entrance"
            },
            ...
        ]
    }
    
    Response:
    {
        "processed": 2,
        "results": [
            {"nfc_uid": "...", "result": "granted", "event_id": 123},
            {"nfc_uid": "...", "result": "denied", "reason": "..."}
        ]
    }
    """
    # Verify JWT token
    device_id, error = verify_device_token()
    if error:
        return error
    
    data = request.get_json(force=True, silent=True) or {}
    scans = data.get("scans", [])
    
    if not isinstance(scans, list):
        return jsonify({"error": "scans must be an array"}), 400
    
    results = []
    
    for scan in scans:
        nfc_uid = scan.get("nfc_uid", "").strip()
        if not nfc_uid:
            continue
        
        # Process each scan (simplified - reuse scan logic)
        with DB() as db:
            user = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
            
            if user and user.estado == "active" and user.nfc_status == "active":
                event = Evento(
                    event="nfc_scan_granted",
                    actor_uid=user.uid,
                    source=device_id,
                    context={
                        "location": scan.get("location", ""),
                        "batch_sync": True,
                        "timestamp": scan.get("timestamp")
                    }
                )
                db.add(event)
                db.flush()
                
                results.append({
                    "nfc_uid": nfc_uid,
                    "result": "granted",
                    "event_id": event.id
                })
            else:
                reason = "card_not_registered"
                if user:
                    if user.estado != "active":
                        reason = "user_inactive"
                    elif user.nfc_status != "active":
                        reason = "card_revoked"
                
                event = Evento(
                    event="nfc_scan_denied",
                    actor_uid=user.uid if user else None,
                    source=device_id,
                    context={
                        "reason": reason,
                        "batch_sync": True,
                        "timestamp": scan.get("timestamp")
                    }
                )
                db.add(event)
                
                results.append({
                    "nfc_uid": nfc_uid,
                    "result": "denied",
                    "reason": reason
                })
    
    return jsonify({
        "processed": len(results),
        "results": results
    })


# ========== HEARTBEAT ==========

@bp.post("/nfc_devices/heartbeat")
def nfc_heartbeat():
    """
    Receive heartbeat from NFC device
    
    Request Body:
    {
        "device_id": "NFC-READER-001",
        "status": "active",
        "stats": {
            "scans_unsynced": 5,
            "battery_level": 85,
            "nfc_enabled": true
        }
    }
    
    Response:
    {
        "ok": true,
        "server_time": "2025-10-26T15:30:00Z",
        "device_status": "active",
        "commands": []
    }
    """
    # Verify JWT token
    device_id, error = verify_device_token()
    if error:
        return error
    
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status", "active")
    stats = data.get("stats", {})
    
    with DB() as db:
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        # Update device
        device.last_seen = now_cst()
        device.status = status
        device.stats_json = stats
        
        return jsonify({
            "ok": True,
            "server_time": now_cst().isoformat(),
            "device_status": device.status,
            "commands": []  # Future: remote commands like "reboot", "update_config"
        })


# ========== DEVICE INFO ==========

@bp.get("/nfc_devices/me")
def nfc_device_info():
    """
    Get device information
    
    Response:
    {
        "id": 1,
        "device_id": "NFC-READER-001",
        "name": "NFC Reader - Entrance",
        "status": "active",
        "location": "Main Entrance",
        "ip": "192.168.1.100",
        "last_seen": "2025-10-26T15:30:00Z",
        "registered_at": "2025-10-20T10:00:00Z",
        "stats": {...}
    }
    """
    # Verify JWT token
    device_id, error = verify_device_token()
    if error:
        return error
    
    with DB() as db:
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        # Get scan statistics
        total_scans = db.query(Evento).filter(
            Evento.source == device_id,
            Evento.event.in_(["nfc_scan_granted", "nfc_scan_denied"])
        ).count()
        
        granted_scans = db.query(Evento).filter(
            Evento.source == device_id,
            Evento.event == "nfc_scan_granted"
        ).count()
        
        return jsonify({
            "id": device.id,
            "device_id": device_id,
            "name": device.name,
            "status": device.status,
            "location": device.location,
            "ip": device.ip,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "registered_at": device.registered_at.isoformat() if device.registered_at else None,
            "stats": {
                "total_scans": total_scans,
                "granted_scans": granted_scans,
                "denied_scans": total_scans - granted_scans,
                **(device.stats_json or {})
            }
        })


# ========== NFC CARD ASSIGNMENT ==========

@bp.post("/nfc/assign")
def nfc_assign():
    """
    Assign NFC card to user (admin only)
    Note: This endpoint should be protected with admin authentication
    
    Request Body:
    {
        "uid": "EMP-001",
        "nfc_uid": "04A3B2C1D4E5F6",
        "nfc_card_id": "CARD-001"
    }
    
    Response:
    {
        "ok": true,
        "user": {
            "uid": "EMP-001",
            "nfc_uid": "04A3B2C1D4E5F6",
            "nfc_status": "active",
            "nfc_issued_at": "2025-10-26T15:30:00Z"
        }
    }
    """
    # TODO: Add admin authentication check here
    # For now, this is open but should be secured in production
    
    data = request.get_json(force=True, silent=True) or {}
    user_uid = data.get("uid", "").strip()
    nfc_uid = data.get("nfc_uid", "").strip()
    nfc_card_id = data.get("nfc_card_id", "")
    
    if not user_uid or not nfc_uid:
        return jsonify({"error": "uid and nfc_uid required"}), 400
    
    with DB() as db:
        # Find user
        user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
        
        if not user:
            return jsonify({"error": f"User {user_uid} not found"}), 404
        
        # Check if NFC UID is already assigned to another user
        existing = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        if existing and existing.uid != user_uid:
            return jsonify({"error": f"NFC UID already assigned to user {existing.uid}"}), 409
        
        # Assign NFC card
        user.nfc_uid = nfc_uid
        user.nfc_uid_hash = hashlib.sha256(nfc_uid.encode()).hexdigest()
        user.nfc_card_id = nfc_card_id or nfc_uid
        user.nfc_status = "active"
        user.nfc_issued_at = now_cst()
        user.nfc_revoked_at = None  # Clear any previous revocation
        
        # Log assignment event
        event = Evento(
            event="nfc_card_assigned",
            actor_uid=user_uid,
            source="admin",
            context={
                "nfc_card_id": nfc_card_id,
                "assigned_at": now_cst().isoformat(),
                "assigned_by": "admin"  # TODO: Get actual admin uid from session
            }
        )
        db.add(event)
        
        return jsonify({
            "ok": True,
            "user": {
                "uid": user.uid,
                "nfc_uid": nfc_uid,
                "nfc_status": user.nfc_status,
                "nfc_issued_at": user.nfc_issued_at.isoformat()
            }
        })


# ========== SERVER CONFIGURATION ==========

@bp.get("/nfc_devices/config")
def nfc_config():
    """
    Get server configuration for NFC devices
    
    Response:
    {
        "heartbeat_interval": 30,
        "scan_timeout": 5,
        "offline_queue_max": 1000,
        "features": {...},
        "server_time": "2025-10-26T15:30:00Z"
    }
    """
    return jsonify({
        "heartbeat_interval": 30,  # seconds
        "scan_timeout": 5,  # seconds
        "offline_queue_max": 1000,  # max scans in offline queue
        "features": {
            "offline_mode": True,
            "batch_sync": True,
            "biometric_auth": False,
            "location_tracking": True
        },
        "server_time": now_cst().isoformat()
    })


# ========== UTILITY: Get User by NFC UID ==========

@bp.get("/nfc/user/<nfc_uid>")
def nfc_get_user(nfc_uid: str):
    """
    Get user by NFC UID (for debugging/admin purposes)
    Note: Should be protected with admin authentication
    
    Response:
    {
        "uid": "EMP-001",
        "nombre": "John",
        "apellido": "Doe",
        "email": "...",
        "rol": "R-EMP",
        "nfc_status": "active",
        "nfc_issued_at": "..."
    }
    """
    # TODO: Add admin authentication check
    
    with DB() as db:
        user = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "uid": user.uid,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "email": user.email,
            "rol": user.rol,
            "estado": user.estado,
            "nfc_uid": user.nfc_uid,
            "nfc_card_id": user.nfc_card_id,
            "nfc_status": user.nfc_status,
            "nfc_issued_at": user.nfc_issued_at.isoformat() if user.nfc_issued_at else None,
            "nfc_revoked_at": user.nfc_revoked_at.isoformat() if user.nfc_revoked_at else None
        })


