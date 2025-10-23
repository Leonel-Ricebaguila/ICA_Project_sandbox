from flask import Blueprint, request, jsonify
from pathlib import Path
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Usuario, Evento, UserDeviceKey
from ..auth import hash_password
from ..qr import gen_qr_value_b32, hash_qr_value
from ..user_qr import save_user_qr_png, resolve_logo
from ..logging_utils import sign_event_and_persist, register_log_listener, unregister_log_listener
from ..req_auth import require_roles
from flask import Response, stream_with_context
import json
import os
import datetime
from ..time_utils import now_cst

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
    """Datos básicos del usuario para el encabezado/perfil del panel.

    Acepta uid en query por compatibilidad, pero si no viene intenta
    resolverlo desde Authorization: Bearer (JWT) para evitar estados
    parciales en el cliente.
    """
    uid = request.args.get("uid")
    with DB() as db:
        if not uid:
            return jsonify(detail="uid required"), 400
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

@bp.get("/users/lookup")
def lookup_user_by_email():
    """Búsqueda simple por email. Devuelve uid y nombre.
    Accesible para usuarios activos de cualquier rol (solo lectura).
    """
    email = request.args.get("email", "").strip().lower()
    requester = request.args.get("uid")
    if not email:
        return jsonify(detail="email required"), 400
    with DB() as db:
        # Verificar requester activo
        r = db.query(Usuario).filter(Usuario.uid == requester).first()
        if not r or r.estado != 'active':
            return jsonify(detail="forbidden"), 403
        u = db.query(Usuario).filter(Usuario.email == email).first()
        if not u:
            return jsonify(detail="not found"), 404
        return jsonify({
            "uid": u.uid,
            "email": u.email,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "rol": u.rol,
        })

@bp.post("/users/devkey")
def publish_device_key():
    """Registra o actualiza la clave pública ECDH del dispositivo del usuario.
    Body: {uid, jwk: { ... }}
    """
    data = request.get_json(force=True, silent=True) or {}
    uid = data.get("uid")
    jwk = data.get("jwk")
    if not uid or not jwk:
        return jsonify(detail="uid, jwk required"), 400
    with DB() as db:
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado == 'active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        rec = db.query(UserDeviceKey).filter(UserDeviceKey.uid == uid).first()
        if not rec:
            rec = UserDeviceKey(uid=uid, algo=jwk.get("kty","ECDH-P256"), pub_jwk=json.dumps(jwk))
            db.add(rec)
        else:
            rec.algo = jwk.get("kty","ECDH-P256")
            rec.pub_jwk = json.dumps(jwk)
        return jsonify(ok=True)

@bp.get("/users/devkey")
def get_device_key():
    """Obtiene la clave pública ECDH del usuario objetivo.
    Query: uid (solicitante), target
    """
    requester = request.args.get("uid")
    target = request.args.get("target")
    if not requester or not target:
        return jsonify(detail="uid, target required"), 400
    with DB() as db:
        r = db.query(Usuario).filter(Usuario.uid == requester, Usuario.estado=='active').first()
        if not r:
            return jsonify(detail="forbidden"), 403
        rec = db.query(UserDeviceKey).filter(UserDeviceKey.uid == target).first()
        if not rec:
            return jsonify(detail="not found"), 404
        try:
            jwk = json.loads(rec.pub_jwk)
        except Exception:
            jwk = {"kty":"EC"}
        return jsonify({"uid": target, "algo": rec.algo, "jwk": jwk})

@bp.get("/users/devkeys")
def get_device_keys_by_role():
    """Lista claves públicas por rol o todas (solo admin).
    Query: uid (solicitante), role=R-*, all=true/false
    """
    requester = request.args.get("uid")
    role = request.args.get("role")
    include_all = request.args.get("all") in ("1","true","yes")
    with DB() as db:
        r = db.query(Usuario).filter(Usuario.uid == requester, Usuario.estado=='active').first()
        if not r:
            return jsonify(detail="forbidden"), 403
        if include_all and r.rol != 'R-ADM':
            return jsonify(detail="forbidden"), 403
        q = db.query(Usuario).filter(Usuario.estado=='active')
        if not include_all:
            if role:
                q = q.filter(Usuario.rol == role)
            else:
                return jsonify(detail="role or all required"), 400
        users = q.all()
        uids = [u.uid for u in users]
        keys = db.query(UserDeviceKey).filter(UserDeviceKey.uid.in_(uids)).all()
        by_uid = {k.uid: k for k in keys}
        out = []
        for u in users:
            k = by_uid.get(u.uid)
            if not k: continue
            try:
                jwk = json.loads(k.pub_jwk)
            except Exception:
                jwk = {"kty":"EC"}
            out.append({"uid": u.uid, "rol": u.rol, "jwk": jwk, "algo": k.algo})
        return jsonify(out)

@bp.get("/users")
def list_users():
    """Lista de usuarios (R-ADM/R-IM/R-AUD)."""
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM", "R-AUD"])  # Auditor solo lectura
        if err: return jsonify(detail=err[0]), err[1]
        rows = db.query(Usuario).all()
        return jsonify([{
            "uid": x.uid, "email": x.email, "nombre": x.nombre, "apellido": x.apellido,
            "rol": x.rol, "estado": x.estado
        } for x in rows])

@bp.put("/users/<uid>")
def update_user(uid: str):
    """Actualiza atributos básicos del usuario (R-ADM/R-IM)."""
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        _, err = require_roles(db, roles=["R-ADM", "R-IM"])  # Auditor sin permisos de modificación
        if err: return jsonify(detail=err[0]), err[1]
        u = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not u: return jsonify(detail="not found"), 404
        for k in ("nombre","apellido","email","rol","estado"):
            if k in data and data[k] is not None:
                setattr(u, k, data[k])
        u.actualizado_en = now_cst()
        return jsonify(ok=True)

@bp.post("/users")
def create_user():
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        _, err = require_roles(db, roles=["R-ADM", "R-IM"])  # sólo admin/IAM
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
        # Auto-asignar QR (hash) antes de commit
        try:
            qr_val = gen_qr_value_b32()
            u.qr_value_hash = hash_qr_value(qr_val)
            # Activar QR por defecto para permitir login inmediato
            try:
                u.qr_status = 'active'
                # Si existe la columna, asignar qr_card_id (por defecto el UID)
                if hasattr(u, 'qr_card_id'):
                    u.qr_card_id = u.qr_card_id or u.uid
            except Exception:
                pass
            # Guardar PNG con tema UPY
            save_user_qr_png(u.uid, qr_val, outdir="cards", size=600)
        except Exception:
            pass
        db.add(u)
        # Registrar creación en bitácora (actor=uid creado para consistencia con CLI)
        try:
            sign_event_and_persist(db, "user_created", actor_uid=u.uid, source="api", context={"rol": u.rol})
        except Exception:
            pass
        return jsonify(ok=True)

@bp.get("/logs")
def get_logs():
    """Últimos eventos (blockchain-like) o delta incremental con since_id."""
    requester = request.args.get("uid")
    since_id = request.args.get("since_id", type=int)
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-MON", "R-AUD"])
        if err: return jsonify(detail=err[0]), err[1]
        # Detectar reinicio de IDs (p.ej., tras wipe) y forzar resync
        max_row = db.query(Evento).order_by(Evento.id.desc()).first()
        current_max = max_row.id if max_row else None
        q = db.query(Evento)
        if since_id is not None and current_max is not None and current_max < since_id:
            # reset detectado → devolver últimos 200
            q = q.order_by(Evento.id.desc()).limit(200)
        elif since_id is not None:
            q = q.filter(Evento.id > since_id).order_by(Evento.id.asc())
        else:
            q = q.order_by(Evento.id.desc()).limit(200)
        rows = q.all()
        resp = jsonify([{
            "id": e.id,
            "tipo": e.event,
            "actor_uid": e.actor_uid,
            "source": e.source,
            "created_at": e.ts.isoformat() if getattr(e, 'ts', None) else None,
            "context": e.context,
        } for e in rows])
        try:
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        except Exception:
            pass
        return resp


@bp.get("/logs/stream")
def stream_logs():
    """SSE: emite eventos de bitácora en tiempo casi real.

    Requiere roles: R-ADM / R-MON / R-AUD.
    """
    requester = request.args.get("uid")
    # autorización por uid (compat)
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-MON", "R-AUD"])
        if err:
            return jsonify(detail=err[0]), err[1]

    def gen():
        q = register_log_listener()
        # Capturar último id existente para emitir sólo nuevos
        last_id = 0
        try:
            from ..models import Evento as _E
            with DB() as _dbsnap:
                last = _dbsnap.query(_E).order_by(_E.id.desc()).first()
                last_id = last.id if last else 0
        except Exception:
            pass
        try:
            yield "event: ping\ndata: {}\n\n"
            idle = 0
            while True:
                pushed = False
                # a) Recibir broadcast local (misma instancia de servidor)
                try:
                    item = q.get(timeout=1)
                    if item and int(item.get("id", 0)) > last_id:
                        data = json.dumps({
                            "id": item.get("id"),
                            "tipo": item.get("event"),
                            "actor_uid": item.get("actor_uid"),
                            "source": item.get("source"),
                            "created_at": item.get("ts"),
                            "context": item.get("context") or {},
                        })
                        yield f"event: log\ndata: {data}\n\n"
                        last_id = int(item.get("id", last_id))
                        pushed = True
                except Exception:
                    pass
                # b) Poll DB por nuevos (cubre eventos creados desde procesos CLI)
                try:
                    from ..models import Evento as _E2
                    with DB() as _dbpoll:
                        # Detectar reinicio de IDs (tras wipe)
                        max_row = _dbpoll.query(_E2).order_by(_E2.id.desc()).first()
                        current_max = max_row.id if max_row else None
                        if current_max is not None and current_max < last_id:
                            last_id = 0
                        rows = _dbpoll.query(_E2).filter(_E2.id > last_id).order_by(_E2.id.asc()).all()
                        for r in rows:
                            data = json.dumps({
                                "id": r.id,
                                "tipo": r.event,
                                "actor_uid": r.actor_uid,
                                "source": r.source,
                                "created_at": r.ts.isoformat() if getattr(r, 'ts', None) else None,
                                "context": r.context or {},
                            })
                            yield f"event: log\ndata: {data}\n\n"
                            last_id = r.id
                            pushed = True
                except Exception:
                    pass
                # Heartbeat periódico si no hubo actividad
                if not pushed:
                    idle += 1
                    if idle >= 5:
                        yield "event: ping\ndata: {}\n\n"
                        idle = 0
                else:
                    idle = 0
        finally:
            unregister_log_listener(q)

    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return Response(stream_with_context(gen()), headers=headers)

@bp.get("/ac/last")
def ac_last():
    """Última autenticación por QR para el panel de Access Control."""
    requester = request.args.get("uid")
    with DB() as db:
        # Compat sin JWT: autoriza por uid con roles R-ADM/R-AC/R-AUD
        _, err = _require_role(db, requester, roles=["R-ADM", "R-AC", "R-AUD"])
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
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM", "R-AUD"])  # Auditor solo lectura
        if err: return jsonify(detail=err[0]), err[1]

        users = db.query(Usuario).all()
        eventos = db.query(Evento).order_by(Evento.id.desc()).limit(300).all()

        # auth_sessions puede no existir en este SessionLocal import, pero está en models
        from ..models import AuthSession, CameraDevice, QRScannerDevice, NFCDevice
        sessions = db.query(AuthSession).order_by(AuthSession.created_at.desc()).limit(300).all()

        resp = jsonify({
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
        try:
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        except Exception:
            pass
        return resp

@bp.post("/log/csv")
def log_csv_download():
    """Registra un evento cuando el usuario descarga un CSV desde el panel.

    Requiere roles: R-ADM/R-IM/R-AUD (mismos que la vista Data Base).
    Parámetros: uid (query o JSON) y table (JSON o query).
    """
    requester = request.args.get("uid")
    payload = request.get_json(force=True, silent=True) or {}
    table = payload.get("table") or request.args.get("table")
    if not table:
        return jsonify(detail="table required"), 400
    with DB() as db:
        _, err = _require_role(db, requester, roles=["R-ADM", "R-IM", "R-AUD"])
        if err: return jsonify(detail=err[0]), err[1]
        try:
            sign_event_and_persist(db, "csv_download", actor_uid=requester, source="ui", context={"table": table})
        except Exception:
            pass
        return jsonify(ok=True)
