from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from .db import Base
from sqlalchemy.orm import relationship
from .time_utils import now_cst

class Usuario(Base):
    __tablename__ = "usuarios"
    uid = Column(String, primary_key=True)  # e.g., EMP-0001
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    rol = Column(String, nullable=False, default="R-EMP")
    estado = Column(String, nullable=False, default="active")
    password_hash = Column(String, nullable=False)
    qr_value_hash = Column(String, nullable=True)   # Argon2 hash
    qr_card_id = Column(String, nullable=True)
    qr_status = Column(String, nullable=True, default="active")
    qr_issued_at = Column(DateTime(timezone=True), default=now_cst)
    qr_revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # NFC Card fields (added for Android app integration)
    nfc_uid = Column(String(32), unique=True, nullable=True)
    nfc_uid_hash = Column(String(64), nullable=True)
    nfc_card_id = Column(String(32), nullable=True)
    nfc_status = Column(String(20), default='inactive', nullable=True)
    nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
    nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    mfa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=now_cst)
    actualizado_en = Column(DateTime(timezone=True), onupdate=now_cst)

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    session_id = Column(String, primary_key=True)
    uid = Column(String, ForeignKey("usuarios.uid"), nullable=True)
    state = Column(String, default="pending")  # pending, mfa_required, completed, failed, expired
    created_at = Column(DateTime(timezone=True), default=now_cst)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    context = Column(JSON, nullable=True)

class Evento(Base):
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), default=now_cst)
    event = Column(String, nullable=False)
    actor_uid = Column(String, nullable=True)
    source = Column(String, nullable=True)
    context = Column(JSON, nullable=True)
    signature = Column(Text, nullable=True)
    hash_prev = Column(String, nullable=True)

# Dispositivos registrados
class CameraDevice(Base):
    __tablename__ = "devices_cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    location = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

class QRScannerDevice(Base):
    __tablename__ = "devices_qr_scanners"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    location = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

class NFCDevice(Base):
    __tablename__ = "devices_nfc"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="active")
    location = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # Device authentication and tracking fields (added for Android app)
    device_id = Column(String(64), unique=True, nullable=True)
    device_secret = Column(String, nullable=True)
    registered_at = Column(DateTime(timezone=True), default=now_cst, nullable=True)
    android_version = Column(String, nullable=True)
    app_version = Column(String, nullable=True)
    stats_json = Column(JSON, nullable=True)

# Mensajes simples por grupo
class Mensaje(Base):
    __tablename__ = "mensajes"
    msg_id = Column(Integer, primary_key=True, index=True)
    remitente_uid = Column(String, ForeignKey("usuarios.uid"), nullable=True)
    grupo = Column(String, nullable=True)
    contenido = Column(Text, nullable=False)
    creado_en = Column(DateTime(timezone=True), default=now_cst)

# Claves públicas de dispositivo (ECDH) por usuario para E2E
class UserDeviceKey(Base):
    __tablename__ = "user_device_keys"
    uid = Column(String, ForeignKey("usuarios.uid"), primary_key=True)
    algo = Column(String, nullable=False, default="ECDH-P256")
    pub_jwk = Column(Text, nullable=False)  # JSON Web Key (solo público)
    creado_en = Column(DateTime(timezone=True), default=now_cst)

# Confirmaciones de lectura por mensaje
class MessageRead(Base):
    __tablename__ = "mensajes_read"
    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(Integer, ForeignKey("mensajes.msg_id"), nullable=False)
    uid = Column(String, ForeignKey("usuarios.uid"), nullable=False)
    read_at = Column(DateTime(timezone=True), default=now_cst)

# Clave de canal (chat) por grupo o DM
class ChannelKey(Base):
    __tablename__ = "channel_keys"
    channel = Column(String, primary_key=True)  # p.ej., IM / Avisos / DM:UID1:UID2 (ordenado)
    # Mapa uid -> ciphertext (clave de canal cifrada para ese usuario con su self-ECDH)
    key_map = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_cst)
    updated_at = Column(DateTime(timezone=True), default=now_cst, onupdate=now_cst)
