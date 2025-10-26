"""
NFC Device & Scanning API Routes
Handles Android NFC app integration for IAM_Backend

This file provides endpoints for:
- NFC card scanning (access control)
- Device heartbeat (monitoring)
- NFC card assignment (admin)

Created: October 26, 2025
For: UPY Sentinel NFC Android App Integration
"""

from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Usuario, NFCDevice, Evento
from ..time_utils import now_cst
import hashlib

bp = Blueprint("nfc", __name__, url_prefix="/api/nfc")

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


# ========== NFC SCANNING ==========

@bp.post("/scan")
def nfc_scan():
    """
    Process NFC card scan and grant/deny access
    
    Request Body:
    {
        "uid": "04A3B2C1D4E5F6",
        "password_valid": true,
        "device_id": "ba899bab96c788b7",
        "session_id": "abc123..."
    }
    
    Response (Granted):
    {
        "result": "granted",
        "user": {...},
        "access_level": "standard",
        "message": "Access granted"
    }
    
    Response (Denied):
    {
        "result": "denied",
        "reason": "card_not_registered",
        "message": "..."
    }
    """
    # Get scan data
    data = request.get_json(force=True, silent=True) or {}
    nfc_uid = data.get("uid", "").strip()
    password_valid = data.get("password_valid", False)
    device_id = data.get("device_id", "")
    session_id = data.get("session_id", "")
    
    if not nfc_uid:
        return jsonify({
            "result": "denied",
            "reason": "invalid_request",
            "message": "uid required",
            "timestamp": now_cst().isoformat()
        }), 400
    
    with DB() as db:
        # Update device last_seen (track activity even for failed attempts)
        if device_id:
            nfc_device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
            if nfc_device:
                nfc_device.last_seen = now_cst()
        
        # Password must be valid - LOG THIS EVENT!
        if not password_valid:
            # Log invalid password attempt
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=None,
                source=device_id or "unknown",
                context={
                    "nfc_uid_truncated": nfc_uid[-4:] if len(nfc_uid) >= 4 else nfc_uid,
                    "reason": "invalid_password",
                    "message": "Password authentication failed"
                }
            )
            db.add(event)
            db.commit()
            
            return jsonify({
                "result": "denied",
                "reason": "invalid_password",
                "message": "NFC card password validation failed",
                "timestamp": now_cst().isoformat()
            })
        
        # Lookup user by NFC UID
        user = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        
        # CASE 1: Card not registered
        if not user:
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=None,
                source=device_id or "unknown",
                context={
                    "nfc_uid_truncated": nfc_uid[-4:] if len(nfc_uid) >= 4 else nfc_uid,
                    "reason": "card_not_registered"
                }
            )
            db.add(event)
            db.commit()  # SAVE TO DATABASE!
            
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
                source=device_id or "unknown",
                context={
                    "reason": "user_inactive",
                    "user_estado": user.estado
                }
            )
            db.add(event)
            db.commit()  # SAVE TO DATABASE!
            
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
                source=device_id or "unknown",
                context={
                    "reason": "card_revoked",
                    "nfc_status": user.nfc_status
                }
            )
            db.add(event)
            db.commit()  # SAVE TO DATABASE!
            
            return jsonify({
                "result": "denied",
                "reason": "card_revoked",
                "message": f"NFC card status: {user.nfc_status}",
                "timestamp": now_cst().isoformat()
            })
        
        # CASE 4: ACCESS GRANTED
        
        # Update user last access
        user.ultimo_acceso = now_cst()
        
        # Update device last_seen timestamp
        if device_id:
            nfc_device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
            if nfc_device:
                nfc_device.last_seen = now_cst()
                print(f"DEBUG: Updated last_seen for device {device_id}")
            else:
                print(f"DEBUG: Device not found with device_id: {device_id}")
        else:
            print(f"DEBUG: No device_id provided in scan request")
        
        # Log success event
        event = Evento(
            event="nfc_scan_granted",
            actor_uid=user.uid,
            source=device_id or "unknown",
            context={
                "device_id": device_id,
                "user_rol": user.rol
            }
        )
        db.add(event)
        db.flush()  # Get event ID
        
        # Determine access level based on role
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
                "email": user.email
            },
            "access_level": access_level,
            "message": "Access granted",
            "event_id": event.id,
            "timestamp": now_cst().isoformat()
        })


# ========== HEARTBEAT ==========

@bp.post("/heartbeat")
def nfc_heartbeat():
    """
    Receive heartbeat from NFC device
    
    Request Body:
    {
        "device_id": "ba899bab96c788b7",
        "status": "active"
    }
    
    Response:
    {
        "ok": true,
        "server_time": "2025-10-26T15:30:00Z"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get("device_id", "").strip()
    
    if not device_id:
        return jsonify({"error": "device_id required"}), 400
    
    with DB() as db:
        # Find or create device
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            # Auto-register device
            device = NFCDevice(
                name=f"Android Device {device_id[:8]}",
                device_id=device_id,
                device_secret="",  # Will be set later
                status="active",
                ip=request.remote_addr,
                registered_at=now_cst()
            )
            db.add(device)
        else:
            # Update existing device
            device.last_seen = now_cst()
            device.ip = request.remote_addr
        
        return jsonify({
            "ok": True,
            "server_time": now_cst().isoformat()
        })


# ========== NFC CARD ASSIGNMENT ==========

@bp.post("/assign")
def nfc_assign():
    """
    Assign NFC card to user (admin only)
    
    Request Body:
    {
        "uid": "EMP-001",
        "nfc_uid": "04A3B2C1D4E5F6"
    }
    
    Response:
    {
        "ok": true,
        "user": {
            "uid": "EMP-001",
            "nfc_uid": "04A3B2C1D4E5F6",
            "nfc_status": "active"
        }
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    user_uid = data.get("uid", "").strip()
    nfc_uid = data.get("nfc_uid", "").strip()
    
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
        user.nfc_card_id = nfc_uid
        user.nfc_status = "active"
        user.nfc_issued_at = now_cst()
        user.nfc_revoked_at = None
        
        # Log assignment event
        event = Evento(
            event="nfc_card_assigned",
            actor_uid=user_uid,
            source="api",
            context={
                "nfc_uid_truncated": nfc_uid[-4:],
                "assigned_at": now_cst().isoformat()
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


# ========== GET DEVICES (Web UI) ==========

@bp.get("/devices")
def nfc_devices():
    """
    Get list of NFC devices (for web UI)
    
    Response:
    {
        "devices": [
            {
                "id": 1,
                "device_id": "ba899bab96c788b7",
                "name": "Android Device ba899bab",
                "status": "active",
                "last_seen": "2025-10-26T15:30:00Z"
            }
        ]
    }
    """
    with DB() as db:
        devices = db.query(NFCDevice).all()
        
        return jsonify({
            "devices": [
                {
                    "id": d.id,
                    "device_id": d.device_id,
                    "name": d.name,
                    "status": d.status,
                    "ip": d.ip,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "registered_at": d.registered_at.isoformat() if d.registered_at else None
                }
                for d in devices
            ]
        })


# ========== ACTIVE DEVICES MONITORING ==========

@bp.get("/devices/active")
def get_active_devices():
    """
    Get list of active NFC reader devices with real-time status
    
    Response:
    {
        "devices": [
            {
                "id": 1,
                "nombre": "NFC Reader 1",
                "device_id": "ba899bab96c788b7",
                "last_seen": "2025-10-26T02:16:25-06:00",
                "status": "online",
                "scans_today": 15,
                "scans_total": 234,
                "registered_at": "2025-10-25T10:00:00-06:00"
            }
        ]
    }
    """
    with DB() as db:
        devices = db.query(NFCDevice).all()
        
        result = []
        for device in devices:
            # Simplified status calculation
            if device.last_seen:
                # Just check if last_seen exists - mark as "active"
                status = "active"
            else:
                status = "never_connected"
            
            # Count today's scans
            today_start = now_cst().replace(hour=0, minute=0, second=0, microsecond=0)
            scans_today = db.query(Evento).filter(
                Evento.source == device.device_id,
                Evento.ts >= today_start,  # Fixed: use 'ts' not 'timestamp'
                Evento.event.like('%nfc_scan%')
            ).count()
            
            # Count total scans
            scans_total = db.query(Evento).filter(
                Evento.source == device.device_id,
                Evento.event.like('%nfc_scan%')
            ).count()
            
            result.append({
                "id": device.id,
                "nombre": device.name or f"Device {device.id}",  # Fixed: use 'name' not 'nombre'
                "device_id": device.device_id,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "status": status,
                "scans_today": scans_today,
                "scans_total": scans_total,
                "registered_at": device.registered_at.isoformat() if device.registered_at else None
            })
        
        return jsonify({
            "devices": result,
            "total": len(result),
            "online_count": sum(1 for d in result if d["status"] == "online")
        })


# ========== ALARM MANAGEMENT ==========

@bp.post("/alarm/stop")
def stop_device_alarm():
    """
    Send stop alarm command to a specific device
    
    Request Body:
    {
        "device_id": "ba899bab96c788b7"
    }
    
    Response:
    {
        "success": true,
        "message": "Stop alarm command sent to device ba899bab96c788b7"
    }
    """
    data = request.get_json() or {}
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({
            "success": False,
            "error": "device_id required"
        }), 400
    
    with DB() as db:
        from sqlalchemy import text
        
        try:
            # Create stop alarm command
            db.execute(text("""
                INSERT INTO alarm_commands (device_id, command, processed)
                VALUES (:device_id, 'stop_alarm', 0)
            """), {"device_id": device_id})
            db.commit()
            
            # Log admin action
            admin_uid = request.args.get('uid', 'system')
            from ..models import Evento
            event = Evento(
                event="alarm_stop_command",
                actor_uid=admin_uid,
                source="web_dashboard",
                context={
                    "target_device": device_id,
                    "action": "stop_alarm"
                }
            )
            db.add(event)
            db.commit()
            
            return jsonify({
                "success": True,
                "message": f"Stop alarm command sent to device {device_id}"
            })
            
        except Exception as e:
            db.rollback()
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


@bp.get("/alarm/status/<device_id>")
def check_alarm_status(device_id):
    """
    Check if device should stop alarm
    
    Response:
    {
        "should_stop": true/false
    }
    """
    with DB() as db:
        from sqlalchemy import text
        
        # Check for unprocessed stop commands
        result = db.execute(text("""
            SELECT id FROM alarm_commands
            WHERE device_id = :device_id
            AND command = 'stop_alarm'
            AND processed = 0
            ORDER BY created_at DESC
            LIMIT 1
        """), {"device_id": device_id}).fetchone()
        
        if result:
            # Mark as processed
            db.execute(text("""
                UPDATE alarm_commands
                SET processed = 1, processed_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": result[0]})
            db.commit()
            
            return jsonify({"should_stop": True})
        
        return jsonify({"should_stop": False})


@bp.get("/alarm/logs")
def get_alarm_logs():
    """
    Get recent alarm-related events for dashboard display
    
    Response:
    {
        "alarm_logs": [
            {
                "id": 123,
                "timestamp": "2025-10-26T12:35:00",
                "event": "nfc_scan_denied",
                "source": "ba899bab96c788b7",
                "context": {"reason": "invalid_password"}
            }
        ]
    }
    """
    limit = request.args.get('limit', 50, type=int)
    
    with DB() as db:
        from sqlalchemy import text
        
        # Get alarm-related events from last 24 hours
        result = db.execute(text("""
            SELECT id, ts, event, source, context
            FROM eventos
            WHERE event IN ('nfc_scan_denied', 'alarm_stop_command', 'alarm_started')
            OR context LIKE '%alarm%'
            ORDER BY id DESC
            LIMIT :limit
        """), {"limit": limit})
        
        logs = []
        for row in result:
            logs.append({
                "id": row[0],
                "timestamp": row[1].isoformat() if row[1] else None,
                "event": row[2],
                "source": row[3],
                "context": row[4]
            })
        
        return jsonify({"alarm_logs": logs, "count": len(logs)})
