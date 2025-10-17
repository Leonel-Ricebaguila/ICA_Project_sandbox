from flask import Blueprint, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import Usuario, Evento
from ..logging_utils import sign_event_and_persist

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@bp.get("/users")
def list_users():
    with db_session() as db:  # type: Session
        users = db.query(Usuario).all()
        return jsonify([
            {"uid": u.uid, "email": u.email, "rol": u.rol, "estado": u.estado,
             "qr_status": u.qr_status, "mfa_enabled": u.mfa_enabled}
            for u in users
        ])

@bp.get("/logs")
def list_logs():
    with db_session() as db:  # type: Session
        events = db.query(Evento).order_by(Evento.id.desc()).limit(50).all()
        return jsonify([
            {"id": e.id, "ts": e.ts, "event": e.event, "actor_uid": e.actor_uid,
             "source": e.source, "context": e.context}
            for e in events
        ])

@bp.post("/users/revoke/<uid>")
def revoke_user(uid: str):
    with db_session() as db:  # type: Session
        user = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not user:
            return jsonify(detail="User not found"), 404
        user.estado = "revoked"; db.commit()
        sign_event_and_persist(db, "user_revoked", actor_uid=uid, source="admin_api", context={})
        return jsonify(ok=True, message=f"User {uid} revoked.")
