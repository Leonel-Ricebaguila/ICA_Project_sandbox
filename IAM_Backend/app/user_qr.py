import os
from typing import Optional

from .db import SessionLocal
from .models import Usuario
from .qr import gen_qr_value_b32, hash_qr_value, save_upy_qr_png
from .logging_utils import sign_event_and_persist


STATIC_LOGO_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "static", "favicon-512.png"),
    os.path.join(os.path.dirname(__file__), "static", "apple-touch-icon.png"),
]


def resolve_logo() -> Optional[str]:
    for p in STATIC_LOGO_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def resolve_outdir(outdir: str) -> str:
    if os.path.isabs(outdir):
        os.makedirs(outdir, exist_ok=True)
        return outdir
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target = os.path.join(proj_root, outdir)
    os.makedirs(target, exist_ok=True)
    return target


def save_user_qr_png(uid: str, qr_value: str, outdir: str = "cards", size: int = 600) -> str:
    outdir = resolve_outdir(outdir)
    logo = resolve_logo()
    png_path = os.path.join(outdir, f"{uid}_QR.png")
    save_upy_qr_png(png_path, qr_value=qr_value, size=int(size), logo_path=logo)
    return png_path


def assign_qr_to_user(uid: str, outdir: str = "cards", size: int = 600, card_id: Optional[str] = None) -> tuple[str, str]:
    """
    Asigna/rota el QR de un usuario, persiste el hash en BD y guarda la imagen PNG.
    Retorna (qr_value, png_path).
    """
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not user:
            raise ValueError("user not found")
        qr_val = gen_qr_value_b32()
        user.qr_value_hash = hash_qr_value(qr_val)
        # Asegurar que el estado del QR esté activo para autenticación
        try:
            if getattr(user, 'qr_status', None) is not None:
                user.qr_status = 'active'
            # Asegurar que quede asignado a una tarjeta (qr_card_id)
            if hasattr(user, 'qr_card_id'):
                user.qr_card_id = card_id or user.qr_card_id or uid
        except Exception:
            pass
        db.commit()
        png_path = save_user_qr_png(uid, qr_val, outdir=outdir, size=size)
        # Registrar en bitácora
        try:
            sign_event_and_persist(db, "qr_assigned", actor_uid=user.uid, source="cli",
                                   context={"qr_card_id": getattr(user, 'qr_card_id', None), "png_path": png_path})
        except Exception:
            pass
        return qr_val, png_path
    finally:
        db.close()
