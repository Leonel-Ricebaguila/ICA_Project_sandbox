from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from .db import Base
from sqlalchemy.orm import relationship

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
    qr_issued_at = Column(DateTime(timezone=True), server_default=func.now())
    qr_revoked_at = Column(DateTime(timezone=True), nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    session_id = Column(String, primary_key=True)
    uid = Column(String, ForeignKey("usuarios.uid"), nullable=True)
    state = Column(String, default="pending")  # pending, mfa_required, completed, failed, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    context = Column(JSON, nullable=True)

class Evento(Base):
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
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
