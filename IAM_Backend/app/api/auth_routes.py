from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import Usuario, AuthSession
from ..auth import verify_password
import uuid, datetime
from ..config import cfg
from ..logging_utils import sign_event_and_persist
from ..attempts import check_lock, register_failure, reset, MAX_ATTEMPTS
from ..time_utils import now_cst

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    with db_session() as db:  # type: Session
        user = db.query(Usuario).filter(Usuario.email == email).first()
        key = (getattr(user, "uid", None) or (email or "").strip().lower())

        remaining = check_lock(key)
        if remaining > 0:
            mins = remaining // 60
            secs = remaining % 60
            human = f"{mins} minutos y {secs} segundos" if mins else f"{secs} segundos"
            sign_event_and_persist(
                db,
                "login_failed_lock_active",
                actor_uid=getattr(user, "uid", None),
                source="auth_api",
                context={"email": email, "remaining_sec": remaining},
            )
            return jsonify(detail=f"Cuenta bloqueada por intentos fallidos. Intenta de nuevo en {human}."), 429

        if not user or not verify_password(password, user.password_hash):
            count, _ = register_failure(key)
            ev = "login_failed_warn" if count == 1 else ("login_failed_timeout" if count == 2 else "login_failed_lock")
            sign_event_and_persist(
                db,
                ev,
                actor_uid=getattr(user, "uid", None),
                source="auth_api",
                context={"email": email, "attempt": count, "max": MAX_ATTEMPTS},
            )
            if count >= MAX_ATTEMPTS:
                return jsonify(detail="Cuenta bloqueada por 10 minutos debido a múltiples intentos fallidos."), 429
            restantes = MAX_ATTEMPTS - count
            return jsonify(detail=f"Credenciales inválidas. Intentos restantes: {restantes}"), 401

        # Crear sesión pendiente para QR (credenciales correctas)
        session_id = str(uuid.uuid4())
        now = now_cst()
        expires_at = now + datetime.timedelta(seconds=cfg.QR_TTL_SECONDS)
        sess = AuthSession(session_id=session_id, uid=user.uid, state="pending", expires_at=expires_at)
        db.add(sess)
        db.commit()

        # Resetear intentos al éxito
        reset(key)

        # Eventos de notificación
        sign_event_and_persist(db, "login_credentials_ok", actor_uid=user.uid, source="auth_api", context={"email": email})
        sign_event_and_persist(
            db,
            "login_success_pending_qr",
            actor_uid=user.uid,
            source="auth_api",
            context={"session_id": session_id, "expires_at": expires_at.isoformat()},
        )

        return jsonify(
            session_id=session_id,
            expires_at=int(expires_at.timestamp()),
            uid=user.uid,
            rol=user.rol,
            next="scan_qr",
        )


@bp.post("/logout")
def logout():
    """Logout server-side: registra evento y es idempotente.

    Acepta `uid` por JSON o query para compatibilidad.
    """
    data = request.get_json(force=True, silent=True) or {}
    uid = data.get("uid") or request.args.get("uid")
    with db_session() as db:  # type: Session
        try:
            sign_event_and_persist(db, "logout", actor_uid=uid, source="auth_api", context={})
        except Exception:
            pass
    return jsonify(ok=True)
