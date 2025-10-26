# app/startup.py — crea el admin por defecto si no existe
from .db import SessionLocal
from .models import Usuario
from .auth import hash_password
from .time_utils import now_cst
from .user_qr import assign_qr_to_user

DEFAULT_ADMIN = {
    "uid": "ADMIN-1",
    "email": "admin@local",
    "password": "StrongPass123!",
    "nombre": "Admin",
    "apellido": "",
    "rol": "R-ADM",
}

def ensure_default_admin():
    db = SessionLocal()
    try:
        u = db.query(Usuario).filter(Usuario.uid == DEFAULT_ADMIN["uid"]).first()
        if u:
            return
        # si no está, lo creamos
        u = Usuario(
            uid=DEFAULT_ADMIN["uid"],
            email=DEFAULT_ADMIN["email"],
            nombre=DEFAULT_ADMIN["nombre"],
            apellido=DEFAULT_ADMIN["apellido"],
            rol=DEFAULT_ADMIN["rol"],
            estado="active",
            password_hash=hash_password(DEFAULT_ADMIN["password"]),
            mfa_enabled=False,
        )
        db.add(u)
        db.commit()
        try:
            assign_qr_to_user(DEFAULT_ADMIN["uid"])  # genera QR y PNG por defecto
        except Exception as e:
            print("[startup] QR assign failed:", e)
        print("[startup] Default admin created:", DEFAULT_ADMIN["uid"], DEFAULT_ADMIN["email"])
    finally:
        db.close()
