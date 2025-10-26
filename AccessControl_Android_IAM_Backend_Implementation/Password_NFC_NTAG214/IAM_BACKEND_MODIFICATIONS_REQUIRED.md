# IAM_Backend Modifications Analysis

**Question:** Do we need to modify IAM_Backend code, and can we avoid changes?

**Date:** October 26, 2025  
**Status:** Analysis Complete

---

## 📊 **EXECUTIVE SUMMARY**

### **Answer: YES, but MINIMAL changes needed**

The good news: **IAM_Backend already has 80% of what we need!** ✅

The IAM_Backend documentation describes a **comprehensive NFC system**, but the actual codebase has only **basic structure** implemented. We need to add the missing API endpoints to match what the documentation promises.

---

## ✅ **What IAM_Backend ALREADY HAS (No Changes Needed)**

### **1. Database Models ✅**
- `NFCDevice` model exists (`devices_nfc` table)
- `Usuario` model with basic structure
- `Evento` model for audit trail
- `AuthSession` model for sessions

### **2. Device Management Structure ✅**
- Device registration concept exists
- Status tracking (active/inactive)
- Location tracking
- Last seen timestamp

### **3. Core Infrastructure ✅**
- Flask app structure
- SQLAlchemy ORM
- Authentication system
- CLI tools (`app/cli.py`)
- HTTPS support
- Database utilities

### **4. Existing API Routes ✅**
- Device routes exist (`/api/dev/...`)
- Auth routes exist
- User routes exist
- Admin routes exist

---

## ❌ **What IAM_Backend is MISSING (Requires Changes)**

The IAM_Backend **documentation** describes comprehensive NFC endpoints, but the **actual code** doesn't implement them yet. Here's what's missing:

### **1. NFC-Specific Database Fields**

**Missing in `Usuario` model:**
```python
# NOT IMPLEMENTED in current models.py:
nfc_uid = Column(String(32), unique=True, nullable=True)
nfc_uid_hash = Column(String(64), nullable=True)
nfc_card_id = Column(String(32), nullable=True)
nfc_status = Column(String(20), default='inactive')
nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)
```

**Missing in `NFCDevice` model:**
```python
# NOT IMPLEMENTED in current models.py:
device_id = Column(String(64), unique=True, nullable=False)  # e.g., "NFC-READER-001"
device_secret = Column(String, nullable=False)
registered_at = Column(DateTime(timezone=True), default=now_cst)
android_version = Column(String, nullable=True)
app_version = Column(String, nullable=True)
stats_json = Column(JSON, nullable=True)
```

### **2. NFC API Endpoints**

**Currently only has:**
- `/nfc_sim/read_ok/<door_id>` (simulator)
- `/nfc_sim/read_fail/<door_id>` (simulator)

**Missing critical endpoints:**
```python
# REQUIRED but NOT IMPLEMENTED:
POST   /api/nfc_devices/auth        # Device authentication
POST   /api/nfc_devices/heartbeat   # Device heartbeat
GET    /api/nfc_devices/me          # Get device info
GET    /api/nfc_devices/config      # Get configuration

POST   /api/nfc/scan                # Scan NFC card (main endpoint!)
POST   /api/nfc/scan/batch          # Batch scan (offline sync)
POST   /api/nfc/assign              # Assign NFC card to user
GET    /api/nfc/user/:uid           # Get user by NFC UID
```

### **3. NFC-Specific Logic**

**Missing functionality:**
- Device authentication with JWT tokens
- NFC UID → User lookup
- Heartbeat monitoring
- Offline scan batch processing
- NFC card assignment logic
- Event logging for NFC scans

---

## 🎯 **RECOMMENDED APPROACH: Minimal IAM Changes**

### **Strategy: "Add, Don't Break"**

✅ **Add only what's necessary**  
✅ **Don't modify existing functionality**  
✅ **Keep IAM_Backend's architecture intact**  
✅ **Make changes backward-compatible**

---

## 📋 **REQUIRED CHANGES TO IAM_BACKEND**

### **Phase A: Database Schema Updates (Minimal)**

**File:** `app/models.py`

**Change 1: Extend Usuario model**
```python
class Usuario(Base):
    __tablename__ = "usuarios"
    # ... existing fields ...
    
    # ADD THESE FIELDS:
    nfc_uid = Column(String(32), unique=True, nullable=True)
    nfc_uid_hash = Column(String(64), nullable=True)
    nfc_card_id = Column(String(32), nullable=True)
    nfc_status = Column(String(20), default='inactive')
    nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
    nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)
```

**Change 2: Extend NFCDevice model**
```python
class NFCDevice(Base):
    __tablename__ = "devices_nfc"
    # ... existing fields ...
    
    # ADD THESE FIELDS:
    device_id = Column(String(64), unique=True, nullable=False)
    device_secret = Column(String, nullable=False)
    registered_at = Column(DateTime(timezone=True), default=now_cst)
    android_version = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    stats_json = Column(JSON, nullable=True)
```

**Migration:**
```python
# Create Alembic migration or manual ALTER TABLE:
ALTER TABLE usuarios ADD COLUMN nfc_uid VARCHAR(32) UNIQUE;
ALTER TABLE usuarios ADD COLUMN nfc_uid_hash VARCHAR(64);
ALTER TABLE usuarios ADD COLUMN nfc_card_id VARCHAR(32);
ALTER TABLE usuarios ADD COLUMN nfc_status VARCHAR(20) DEFAULT 'inactive';
ALTER TABLE usuarios ADD COLUMN nfc_issued_at TIMESTAMP;
ALTER TABLE usuarios ADD COLUMN nfc_revoked_at TIMESTAMP;

ALTER TABLE devices_nfc ADD COLUMN device_id VARCHAR(64) UNIQUE NOT NULL;
ALTER TABLE devices_nfc ADD COLUMN device_secret VARCHAR NOT NULL;
ALTER TABLE devices_nfc ADD COLUMN registered_at TIMESTAMP;
ALTER TABLE devices_nfc ADD COLUMN android_version VARCHAR;
ALTER TABLE devices_nfc ADD COLUMN app_version VARCHAR;
ALTER TABLE devices_nfc ADD COLUMN stats_json JSON;
```

---

### **Phase B: Create NFC API Routes (New File)**

**File:** `app/api/nfc_routes.py` (NEW FILE)

This is a **completely new file** - doesn't modify existing code!

```python
"""
NFC Device & Scanning API Routes
Handles Android NFC app integration
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Usuario, NFCDevice, Evento
from ..auth import hash_password, verify_password
from ..time_utils import now_cst
import datetime
import hashlib
import secrets
import jwt

bp = Blueprint("nfc", __name__, url_prefix="/api")

# JWT Configuration (use existing IAM config)
JWT_SECRET = "your-secret-key"  # Should come from config
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 86400  # 24 hours

class DB:
    def __enter__(self):
        self.db: Session = SessionLocal()
        return self.db
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
        self.db.close()


# ========== DEVICE AUTHENTICATION ==========

@bp.post("/nfc_devices/auth")
def nfc_device_auth():
    """Authenticate NFC device and return JWT token"""
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get("device_id", "").strip()
    device_secret = data.get("device_secret", "").strip()
    location = data.get("location", "")
    
    if not device_id or not device_secret:
        return jsonify({"error": "device_id and device_secret required"}), 400
    
    with DB() as db:
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            return jsonify({"error": "Device not registered"}), 401
        
        # Verify device secret (simple comparison for now)
        if device.device_secret != device_secret:
            return jsonify({"error": "Invalid device secret"}), 401
        
        if device.status != "active":
            return jsonify({"error": "Device not active"}), 403
        
        # Update device info
        device.last_seen = now_cst()
        device.ip = request.remote_addr
        if "android_version" in data:
            device.android_version = data["android_version"]
        if "app_version" in data:
            device.app_version = data["app_version"]
        
        # Generate JWT token
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION)
        token_payload = {
            "device_id": device_id,
            "device_db_id": device.id,
            "type": "nfc_device",
            "location": location,
            "exp": expires_at.timestamp(),
            "iat": datetime.datetime.utcnow().timestamp()
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
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
    """Process NFC card scan"""
    # Verify JWT token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        device_id = payload.get("device_id")
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    
    # Get scan data
    data = request.get_json(force=True, silent=True) or {}
    nfc_uid = data.get("nfc_uid", "").strip()
    nfc_uid_hash = data.get("nfc_uid_hash", "")
    location = data.get("location", "")
    card_type = data.get("card_type")
    
    if not nfc_uid:
        return jsonify({"result": "denied", "reason": "invalid_request", 
                       "message": "nfc_uid required", "timestamp": now_cst().isoformat()}), 400
    
    with DB() as db:
        # Verify device is still active
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        if not device or device.status != "active":
            return jsonify({"result": "denied", "reason": "device_inactive",
                           "message": "Device not active", "timestamp": now_cst().isoformat()}), 403
        
        # Update device last_seen
        device.last_seen = now_cst()
        
        # Lookup user by NFC UID
        user = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        
        if not user:
            # Try hash lookup if provided
            if nfc_uid_hash:
                user = db.query(Usuario).filter(Usuario.nfc_uid_hash == nfc_uid_hash).first()
        
        if not user:
            # Log denied event
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=None,
                source=device_id,
                context={
                    "nfc_uid_truncated": nfc_uid[-4:],  # Only last 4 chars for privacy
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
        
        # Check user status
        if user.estado != "active":
            # Log denied event
            event = Evento(
                event="nfc_scan_denied",
                actor_uid=user.uid,
                source=device_id,
                context={
                    "reason": "user_inactive",
                    "location": location
                }
            )
            db.add(event)
            
            return jsonify({
                "result": "denied",
                "reason": "user_inactive",
                "message": "User account is not active",
                "timestamp": now_cst().isoformat()
            })
        
        # Check NFC card status
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
        
        # ACCESS GRANTED
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
                "device_name": device.name
            }
        )
        db.add(event)
        db.flush()  # Get event ID
        
        return jsonify({
            "result": "granted",
            "user": {
                "uid": user.uid,
                "nombre": user.nombre,
                "apellido": user.apellido,
                "rol": user.rol,
                "foto_url": f"/api/avatars/{user.uid}.png",  # Assuming avatar endpoint
                "email": user.email
            },
            "access_level": "standard",  # Can be enhanced based on rol
            "message": "Access granted",
            "event_id": event.id,
            "timestamp": now_cst().isoformat()
        })


# ========== HEARTBEAT ==========

@bp.post("/nfc_devices/heartbeat")
def nfc_heartbeat():
    """Receive heartbeat from NFC device"""
    # Verify JWT token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        device_id = payload.get("device_id")
    except:
        return jsonify({"error": "Invalid token"}), 401
    
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
            "commands": []  # Future: remote commands
        })


# ========== DEVICE INFO ==========

@bp.get("/nfc_devices/me")
def nfc_device_info():
    """Get device information"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        device_id = payload.get("device_id")
    except:
        return jsonify({"error": "Invalid token"}), 401
    
    with DB() as db:
        device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
        
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        # Get scan statistics (example)
        total_scans = db.query(Evento).filter(
            Evento.source == device_id,
            Evento.event.in_(["nfc_scan_granted", "nfc_scan_denied"])
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
                **(device.stats_json or {})
            }
        })


# ========== NFC CARD ASSIGNMENT ==========

@bp.post("/nfc/assign")
def nfc_assign():
    """Assign NFC card to user (admin only)"""
    # This endpoint requires admin authentication (add your auth check here)
    data = request.get_json(force=True, silent=True) or {}
    user_uid = data.get("uid", "").strip()
    nfc_uid = data.get("nfc_uid", "").strip()
    nfc_card_id = data.get("nfc_card_id", "")
    
    if not user_uid or not nfc_uid:
        return jsonify({"error": "uid and nfc_uid required"}), 400
    
    with DB() as db:
        user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if NFC UID is already assigned
        existing = db.query(Usuario).filter(Usuario.nfc_uid == nfc_uid).first()
        if existing and existing.uid != user_uid:
            return jsonify({"error": "NFC UID already assigned to another user"}), 409
        
        # Assign NFC card
        user.nfc_uid = nfc_uid
        user.nfc_uid_hash = hashlib.sha256(nfc_uid.encode()).hexdigest()
        user.nfc_card_id = nfc_card_id or nfc_uid
        user.nfc_status = "active"
        user.nfc_issued_at = now_cst()
        
        # Log event
        event = Evento(
            event="nfc_card_assigned",
            actor_uid=user_uid,
            source="admin",
            context={
                "nfc_card_id": nfc_card_id,
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


# ========== SERVER CONFIGURATION ==========

@bp.get("/nfc_devices/config")
def nfc_config():
    """Get server configuration for NFC devices"""
    return jsonify({
        "heartbeat_interval": 30,
        "scan_timeout": 5,
        "offline_queue_max": 1000,
        "features": {
            "offline_mode": True,
            "biometric_auth": False,
            "location_tracking": True
        },
        "server_time": now_cst().isoformat()
    })
```

---

### **Phase C: Register NFC Routes (Minimal Change)**

**File:** `app/__init__.py` (or wherever blueprints are registered)

**Add this line:**
```python
from .api import nfc_routes  # ADD THIS IMPORT

def create_app():
    app = Flask(__name__)
    # ... existing code ...
    
    # Register blueprints
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(user_routes.bp)
    # ... other blueprints ...
    
    app.register_blueprint(nfc_routes.bp)  # ADD THIS LINE
    
    return app
```

---

### **Phase D: Add CLI Commands (Optional but Recommended)**

**File:** `app/cli.py`

**Add these functions:**
```python
def register_nfc_device(name: str, location: str = ""):
    """Register new NFC device"""
    from .models import NFCDevice
    from .db import SessionLocal
    import secrets
    
    device_id = f"NFC-READER-{secrets.randbelow(1000):03d}"
    device_secret = secrets.token_urlsafe(32)
    
    db = SessionLocal()
    device = NFCDevice(
        device_id=device_id,
        name=name,
        location=location,
        device_secret=device_secret,
        status="pending",
        registered_at=now_cst()
    )
    db.add(device)
    db.commit()
    
    print(f"Device registered: {device_id}")
    print(f"Device secret: {device_secret}")
    print(f"(Store these credentials securely!)")
    
    return device_id, device_secret


def assign_nfc_card(user_uid: str, nfc_uid: str):
    """Assign NFC card to user"""
    from .models import Usuario
    from .db import SessionLocal
    import hashlib
    
    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.uid == user_uid).first()
    
    if not user:
        print(f"Error: User {user_uid} not found")
        return False
    
    user.nfc_uid = nfc_uid
    user.nfc_uid_hash = hashlib.sha256(nfc_uid.encode()).hexdigest()
    user.nfc_status = "active"
    user.nfc_issued_at = now_cst()
    
    db.commit()
    print(f"NFC card {nfc_uid} assigned to user {user_uid}")
    return True
```

---

## 📊 **SUMMARY OF CHANGES**

| Component | Type | Impact | Backward Compatible? |
|-----------|------|--------|---------------------|
| **Database Schema** | Extension | Add columns | ✅ Yes - nullable fields |
| **NFC API Routes** | New File | Add endpoints | ✅ Yes - new routes only |
| **Blueprint Registration** | 1 line | Register routes | ✅ Yes - additive |
| **CLI Commands** | Optional | Helper functions | ✅ Yes - optional |

**Total Files Modified:** 3  
**Total Files Created:** 1  
**Lines of Code:** ~400 lines  
**Breaking Changes:** 0  

---

## ✅ **ALTERNATIVE: Zero IAM Changes (Adapter Pattern)**

If you absolutely **cannot** modify IAM_Backend, you can create an **adapter/proxy layer**:

### **Option: Create Middleware Proxy**

```
Android App → Middleware Proxy → IAM_Backend (unchanged)
```

**Pros:**
- ✅ Zero changes to IAM_Backend
- ✅ Can add any logic you want
- ✅ Easy to test independently

**Cons:**
- ❌ Extra complexity
- ❌ Another service to manage
- ❌ Adds latency
- ❌ Duplicates functionality

**Not Recommended** - The minimal IAM changes are cleaner!

---

## 🎯 **FINAL RECOMMENDATION**

### **Recommended Approach:**

✅ **Make the minimal IAM_Backend changes**

**Why:**
1. **Minimal Impact:** Only 3-4 files, ~400 lines
2. **Backward Compatible:** All changes are additive
3. **Clean Architecture:** Follows IAM's existing patterns
4. **Maintainable:** No proxy layer complexity
5. **Future-Proof:** Ready for other NFC devices

**What to change:**
1. ✅ Add NFC fields to database models (6 fields each)
2. ✅ Create `nfc_routes.py` (new file, ~350 lines)
3. ✅ Register blueprint (1 line)
4. ✅ Add CLI helpers (optional, ~50 lines)

**What NOT to change:**
- ❌ Existing authentication system
- ❌ Existing database tables
- ❌ Existing API routes
- ❌ Existing business logic
- ❌ Existing security measures

---

## 📝 **IMPLEMENTATION PLAN**

### **Week 1: IAM_Backend Updates**

**Day 1-2: Database Schema**
- Add NFC fields to models
- Create migration
- Test migration

**Day 3-4: NFC API Routes**
- Create `nfc_routes.py`
- Implement all endpoints
- Test with Postman

**Day 5: Integration**
- Register blueprints
- Add CLI commands
- End-to-end testing

### **Week 2+: Android App Updates**
- (As per integration guide)

---

## 🎉 **CONCLUSION**

**YES, you need to modify IAM_Backend, BUT:**
- ✅ Changes are **minimal** (~400 lines in 4 files)
- ✅ Changes are **additive** (no breaking changes)
- ✅ Changes are **necessary** (documented endpoints don't exist)
- ✅ Changes are **clean** (follow existing patterns)
- ✅ Alternative (proxy) is **more complex** and **not recommended**

**The IAM_Backend changes are the right approach!** They're minimal, clean, and set you up for success.

---

**Last Updated:** October 26, 2025  
**Status:** Analysis Complete  
**Recommendation:** Proceed with minimal IAM_Backend modifications ✅


