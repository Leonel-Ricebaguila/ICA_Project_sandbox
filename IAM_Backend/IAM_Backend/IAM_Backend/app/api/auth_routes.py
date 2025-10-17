from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import Usuario, AuthSession
from ..auth import verify_password
import uuid, datetime
from ..config import cfg
from ..logging_utils import sign_event_and_persist

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    with db_session() as db:  # type: Session
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            sign_event_and_persist(db, "login_failed", actor_uid=getattr(user, "uid", None),
                                   source="auth_api", context={"email": email})
            return jsonify(detail="Bad credentials"), 401
        session_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(seconds=cfg.QR_TTL_SECONDS)
        sess = AuthSession(session_id=session_id, uid=user.uid, state="pending", expires_at=expires_at)
        db.add(sess); db.commit()
        sign_event_and_persist(db, "login_success_pending_qr", actor_uid=user.uid,
                               source="auth_api", context={"session_id": session_id, "expires_at": expires_at.isoformat()})
        # Frontend espera además uid y rol para preparar el panel.
        return jsonify(
            session_id=session_id,
            expires_at=int(expires_at.timestamp()),
            uid=user.uid,
            rol=user.rol,
            next="scan_qr"
        )
