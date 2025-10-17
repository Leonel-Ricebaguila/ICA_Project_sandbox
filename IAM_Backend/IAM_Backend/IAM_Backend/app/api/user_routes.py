from flask import Blueprint, request, jsonify
from pathlib import Path
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Usuario, Evento
from ..auth import hash_password
import datetime

bp = Blueprint("users", __name__, url_prefix="/api")

#
# Rutas de datos de usuario y vistas tipo panel
# - /users/me        → datos del usuario (para perfil)
# - /users           → lista (restringido por rol)
# - /users/<uid>     → update (R-ADM/R-IM)
# - /logs            → últimos eventos firmados (R-ADM/R-MON)
# - /ac/last         → última autenticación por QR (R-ADM/R-AC)
# - /db/all          → dump compacto para la pestaña "Data Base"
#

# Utilidad simple para abrir/cerrar sesión DB
class DB:
    def __init__(self):
        self.db: Session | None = None
    def __enter__(self):
        self.db = SessionLocal()
        return self.db
    def __exit__(self, exc_type, exc, tb):
        if self.db is not None:
            if exc_type is None:
                self.db.commit()
            else:
                self.db.rollback()
            self.db.close()

def _require_role(db: Session, requester_uid: str, roles: list[str]):
    u = db.query(Usuario).filter(Usuario.uid == requester_uid).first()
    if not u or u.estado != "active":
        return None, ("user not active", 403)
    if u.rol not in roles:
        return None, ("forbidden", 403)
    return u, None


def _avatar_url_for(uid: str) -> str:
    """Devuelve URL estática del avatar si existe un archivo con el nombre del UID.
    Busca en app/static/avatars/<UID>.(png|jpg|jpeg|webp). Si no, retorna '/static/avatar.png'.
    """
    root = Path(__file__).resolve().parents[1]  # app/
    avatars = root / 'static' / 'avatars'
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        p = avatars / f"{uid}{ext}"
        if p.exists():
            # static_url_path="/" -> los archivos estaticos viven en la raíz
            return f"/avatars/{uid}{ext}"
    return "/avatar.png"

@bp.get("/users/me")
def me():
    """Datos básicos del usuario para el encabezado/perfil del panel."""
    uid = request.args.get("uid")
    if not uid:
        return jsonify(detail="uid required"), 400
    with DB() as db:
        u = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not u:
            return jsonify(detail="not found"), 404
        return jsonify({
            "uid": u.uid,
            "email": u.email,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "rol": u.rol,
            "estado": u.estado,
            "ultimo_acceso": u.ultimo_acceso.isoformat() if u.ultimo_acceso else None,
            "foto_url": _avatar_url_for(u.uid),
        })

@bp.get("/users")
def list_users():
    """Lista de usuarios (sólo para R-ADM/R-IM)."""
    requester = request.args.get("uid")
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM"])
        if err: return jsonify(detail=err[0]), err[1]
        rows = db.query(Usuario).all()
        return jsonify([{
            "uid": x.uid, "email": x.email, "nombre": x.nombre, "apellido": x.apellido,
            "rol": x.rol, "estado": x.estado
        } for x in rows])

@bp.put("/users/<uid>")
def update_user(uid: str):
    """Actualiza atributos básicos del usuario (R-ADM/R-IM)."""
    requester = request.args.get("uid")
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM"])
        if err: return jsonify(detail=err[0]), err[1]
        u = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not u: return jsonify(detail="not found"), 404
        for k in ("nombre","apellido","email","rol","estado"):
            if k in data and data[k] is not None:
                setattr(u, k, data[k])
        u.actualizado_en = datetime.datetime.utcnow()
        return jsonify(ok=True)

@bp.post("/users")
def create_user():
    requester = request.args.get("uid")
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM"])
        if err: return jsonify(detail=err[0]), err[1]
        if not data.get("uid") or not data.get("email") or not data.get("password"):
            return jsonify(detail="uid, email, password required"), 400
        if db.query(Usuario).filter(Usuario.uid==data["uid"]).first():
            return jsonify(detail="uid exists"), 409
        u = Usuario(
            uid=data["uid"],
            email=data["email"],
            nombre=data.get("nombre",""),
            apellido=data.get("apellido",""),
            rol=data.get("rol","R-EMP"),
            estado="active",
            password_hash=hash_password(data["password"]),
        )
        db.add(u)
        return jsonify(ok=True)

@bp.get("/logs")
def get_logs():
    """Últimos eventos (blockchain-like con firma y hash previo)."""
    requester = request.args.get("uid")
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-MON"])
        if err: return jsonify(detail=err[0]), err[1]
        rows = db.query(Evento).order_by(Evento.id.desc()).limit(200).all()
        return jsonify([{
            "id": e.id,
            "tipo": e.event,  # compat con frontend
            "actor_uid": e.actor_uid,
            "source": e.source,
            "created_at": e.ts.isoformat() if getattr(e, 'ts', None) else None,
            "context": e.context,
        } for e in rows])

@bp.get("/ac/last")
def ac_last():
    """Última autenticación por QR para el panel de Access Control."""
    requester = request.args.get("uid")
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-AC"])
        if err: return jsonify(detail=err[0]), err[1]
        ev = db.query(Evento).filter(Evento.event == "qr_scanned_ok").order_by(Evento.id.desc()).first()
        if not ev:
            return jsonify(detail="no events"), 404
        u = db.query(Usuario).filter(Usuario.uid == ev.actor_uid).first()
        return jsonify({
            "when": ev.ts.isoformat() if getattr(ev, 'ts', None) else None,
            "uid": u.uid if u else ev.actor_uid,
            "nombre": (u.nombre + " " + (u.apellido or "")).strip() if u else "",
            "rol": u.rol if u else None,
            "foto_url": _avatar_url_for(u.uid) if u else "/avatar.png"
        })

@bp.get("/db/all")
def db_all():
    """Devuelve dump sencillo de las tablas principales para vista 'Data Base'."""
    requester = request.args.get("uid")
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM"])
        if err: return jsonify(detail=err[0]), err[1]

        users = db.query(Usuario).all()
        eventos = db.query(Evento).order_by(Evento.id.desc()).limit(300).all()

        # auth_sessions puede no existir en este SessionLocal import, pero está en models
        from ..models import AuthSession, CameraDevice, QRScannerDevice, NFCDevice
        sessions = db.query(AuthSession).order_by(AuthSession.created_at.desc()).limit(300).all()

        return jsonify({
            "usuarios": [{
                "uid": u.uid,
                "nombre": u.nombre,
                "apellido": u.apellido,
                "email": u.email,
                "rol": u.rol,
                "estado": u.estado,
                "qr_status": u.qr_status,
                "qr_card_id": u.qr_card_id,
                "ultimo_acceso": u.ultimo_acceso.isoformat() if u.ultimo_acceso else None,
            } for u in users],
            "eventos": [{
                "id": e.id,
                "event": e.event,
                "actor_uid": e.actor_uid,
                "source": e.source,
                "ts": e.ts.isoformat() if getattr(e, 'ts', None) else None,
                "context": e.context,
            } for e in eventos],
            "auth_sessions": [{
                "session_id": s.session_id,
                "uid": s.uid,
                "state": s.state,
                "created_at": s.created_at.isoformat() if getattr(s, 'created_at', None) else None,
                "expires_at": s.expires_at.isoformat() if getattr(s, 'expires_at', None) else None,
            } for s in sessions],
            "devices": {
                "cameras": [{
                    "id": d.id, "name": d.name, "ip": d.ip, "url": d.url,
                    "status": d.status, "location": d.location,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None
                } for d in db.query(CameraDevice).all()],
                "qr_scanners": [{
                    "id": d.id, "name": d.name, "ip": d.ip, "url": d.url,
                    "status": d.status, "location": d.location,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None
                } for d in db.query(QRScannerDevice).all()],
                "nfc": [{
                    "id": d.id, "name": d.name, "ip": d.ip, "port": d.port,
                    "status": d.status, "location": d.location,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None
                } for d in db.query(NFCDevice).all()],
            }
        })
