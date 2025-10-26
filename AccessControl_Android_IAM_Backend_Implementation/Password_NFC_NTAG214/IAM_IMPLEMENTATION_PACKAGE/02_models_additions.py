"""
Database Model Additions for NFC Support

These code snippets should be ADDED to existing models in app/models.py
DO NOT replace existing code, only ADD these fields to existing classes.

Instructions:
1. Open app/models.py in IAM_Backend
2. Find the Usuario class
3. Add the NFC fields shown below (Section A)
4. Find the NFCDevice class
5. Add the device fields shown below (Section B)
"""

# ============================================================
# SECTION A: ADD TO Usuario CLASS
# ============================================================

"""
Location: app/models.py -> class Usuario(Base)

Add these fields to the Usuario class (after existing QR fields):
"""

# NFC Card fields (add after qr_revoked_at field)
nfc_uid = Column(String(32), unique=True, nullable=True)
nfc_uid_hash = Column(String(64), nullable=True)
nfc_card_id = Column(String(32), nullable=True)
nfc_status = Column(String(20), default='inactive', nullable=True)
nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)

# ============================================================
# EXAMPLE: How Usuario class should look AFTER adding fields
# ============================================================

"""
class Usuario(Base):
    __tablename__ = "usuarios"
    uid = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    rol = Column(String, nullable=False, default="R-EMP")
    estado = Column(String, nullable=False, default="active")
    password_hash = Column(String, nullable=False)
    
    # QR fields (existing)
    qr_value_hash = Column(String, nullable=True)
    qr_card_id = Column(String, nullable=True)
    qr_status = Column(String, nullable=True, default="active")
    qr_issued_at = Column(DateTime(timezone=True), default=now_cst)
    qr_revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # ADD THESE NFC FIELDS ↓↓↓
    nfc_uid = Column(String(32), unique=True, nullable=True)
    nfc_uid_hash = Column(String(64), nullable=True)
    nfc_card_id = Column(String(32), nullable=True)
    nfc_status = Column(String(20), default='inactive', nullable=True)
    nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
    nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)
    # ↑↑↑ END OF NFC FIELDS
    
    # ... rest of existing fields ...
    mfa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_cst)
    actualizado_en = Column(DateTime(timezone=True), onupdate=now_cst)
"""


# ============================================================
# SECTION B: ADD TO NFCDevice CLASS
# ============================================================

"""
Location: app/models.py -> class NFCDevice(Base)

Add these fields to the NFCDevice class (after existing fields):
"""

# Device authentication and tracking fields (add after last_seen field)
device_id = Column(String(64), unique=True, nullable=False)
device_secret = Column(String, nullable=False)
registered_at = Column(DateTime(timezone=True), default=now_cst, nullable=True)
android_version = Column(String, nullable=True)
app_version = Column(String, nullable=True)
stats_json = Column(JSON, nullable=True)

# ============================================================
# EXAMPLE: How NFCDevice class should look AFTER adding fields
# ============================================================

"""
class NFCDevice(Base):
    __tablename__ = "devices_nfc"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="active")
    location = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # ADD THESE FIELDS ↓↓↓
    device_id = Column(String(64), unique=True, nullable=False)
    device_secret = Column(String, nullable=False)
    registered_at = Column(DateTime(timezone=True), default=now_cst, nullable=True)
    android_version = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    stats_json = Column(JSON, nullable=True)
    # ↑↑↑ END OF NEW FIELDS
"""


# ============================================================
# IMPORTANT NOTES
# ============================================================

"""
1. These are ADDITIONS only - do NOT remove any existing fields

2. Import requirements (should already be in models.py):
   - from sqlalchemy import Column, String, DateTime, JSON
   - from .time_utils import now_cst

3. The 'nullable=True' means these fields won't break existing data

4. The 'unique=True' constraints are for:
   - Usuario.nfc_uid (one card per user)
   - NFCDevice.device_id (one ID per device)

5. After adding these fields, you MUST run a database migration
   (see 03_migration_script.py)

6. Field descriptions:
   
   Usuario NFC fields:
   - nfc_uid: The actual NFC card UID (e.g., "04A3B2C1D4E5F6")
   - nfc_uid_hash: SHA-256 hash for privacy-preserving lookups
   - nfc_card_id: Physical card identifier (e.g., "CARD-001")
   - nfc_status: active/inactive/revoked/lost
   - nfc_issued_at: When card was assigned
   - nfc_revoked_at: When card was revoked (if applicable)
   
   NFCDevice fields:
   - device_id: Human-readable ID for Android app (e.g., "NFC-READER-001")
   - device_secret: Secret key for device authentication
   - registered_at: When device was registered
   - android_version: Android OS version (e.g., "13")
   - app_version: App version (e.g., "1.0.0")
   - stats_json: Flexible JSON field for device statistics

7. These fields mirror the existing QR fields pattern in Usuario class
"""

# ============================================================
# VERIFICATION CHECKLIST
# ============================================================

"""
After adding these fields, verify:

☐ Usuario class has 6 new nfc_* fields
☐ NFCDevice class has 6 new fields (device_id, device_secret, etc.)
☐ No syntax errors (check indentation matches existing code)
☐ Imports are present (Column, String, DateTime, JSON, now_cst)
☐ Ready to run migration (next step: 03_migration_script.py)
"""


