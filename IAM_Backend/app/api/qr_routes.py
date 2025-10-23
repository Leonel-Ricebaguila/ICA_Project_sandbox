from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import AuthSession, Usuario
from ..qr import verify_qr_value, hash_qr_value, qr_value_fingerprint
from ..auth import create_jwt
from ..logging_utils import sign_event_and_persist
from ..attempts import check_lock, register_failure
from ..time_utils import now_cst, ensure_cst
import datetime

# Robust decoder
import io
import numpy as np
import cv2
from PIL import Image, UnidentifiedImageError

bp = Blueprint("qr", __name__, url_prefix="/api/qr")

#
# Rutas de QR
# - /scan   → valida un valor de QR contra la sesión de login abierta
# - /assign → asigna (o rota) un QR a un usuario (admin)
# - /revoke → revoca un QR de un usuario
# - /decode → fallback universal: el servidor intenta decodificar un QR desde una imagen
#


@bp.post("/scan")
def scan_qr():
    """Valida el QR leído durante la ventana corta de login.

    Flujo esperado:
    1) El frontend hace /api/auth/login → crea AuthSession con state=pending.
    2) En qr.html se lee un QR; aquí se compara con todos los usuarios activos.
    3) Si hay match y el QR pertenece al mismo UID de la sesión → state=completed.
       El frontend continúa a app.html y habilita la sesión larga.
    4) Si no hay match → 401 hash_miss. Si el QR es de otro usuario → 403 mismatch.
    5) Si la sesión expiró → 400 session_expired.
    """
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    qr_value = data.get("qr_value")

    with db_session() as db:  # type: Session
        sess = db.query(AuthSession).filter(AuthSession.session_id == session_id).first()
        if not sess:
            # Loggear explícitamente el caso de sesión inexistente
            sign_event_and_persist(db, "qr_session_not_found", actor_uid=None, source="qr_api",
                                   context={"session_id": session_id})
            return jsonify(detail="session not found"), 404
        exp = ensure_cst(sess.expires_at)
        if exp and exp < now_cst():
            sess.state = "expired"; db.commit()
            # Alerta amarilla por timeout/expiración
            sign_event_and_persist(db, "qr_session_expired", actor_uid=sess.uid, source="qr_api",
                                   context={"session_id": sess.session_id})
            return jsonify(detail="session expired", reason="session_expired"), 400

        # Si el usuario está bloqueado por intentos, rechazar
        remaining = check_lock(sess.uid)
        if remaining > 0:
            mins = remaining // 60
            secs = remaining % 60
            human = f"{mins} minutos y {secs} segundos" if mins else f"{secs} segundos"
            sign_event_and_persist(db, "login_failed_lock_active", actor_uid=sess.uid, source="qr_api",
                                   context={"session_id": sess.session_id, "remaining_sec": remaining})
            return jsonify(detail=f"Cuenta bloqueada. Intenta de nuevo en {human}."), 429

        # 1) Fast‑path: probar primero contra el usuario de la sesión
        matched = None
        sess_user = db.query(Usuario).filter(Usuario.uid == sess.uid).first()
        if sess_user and getattr(sess_user, 'qr_value_hash', None):
            try:
                if verify_qr_value(qr_value, sess_user.qr_value_hash):
                    matched = sess_user
            except Exception:
                pass
        # 2) Si no coincide, buscar en el resto (omitir revocados si existe ese estado)
        users = db.query(Usuario).all()
        if not matched:
            for u in users:
                try:
                    if getattr(u, "qr_status", None) == "revoked":
                        continue
                except Exception:
                    pass
                if u.qr_value_hash and verify_qr_value(qr_value, u.qr_value_hash):
                    matched = u
                    break

        if not matched:
            sess.state = "failed"; db.commit()
            # Registrar intento fallido vinculado al UID de la sesión
            count, _ = register_failure(sess.uid)
            ev = "qr_scanned_fail"  # se mantiene para compatibilidad
            sign_event_and_persist(db, ev, actor_uid=sess.uid, source="qr_api",
                                   context={"session_id": sess.session_id, "reason":"hash_miss", "attempt": count, "fp": qr_value_fingerprint(qr_value)})
            return jsonify(detail="QR not recognized", reason="hash_miss"), 401

        if sess.uid != matched.uid:
            sess.state = "failed"; db.commit()
            count, _ = register_failure(sess.uid)
            # Registro explícito de intento de usar QR ajeno
            sign_event_and_persist(
                db,
                "qr_scanned_mismatch",
                actor_uid=sess.uid,
                source="qr_api",
                context={
                    "session_id": sess.session_id,
                    "attempt": count,
                    "expected_uid": sess.uid,
                    "scanned_uid": matched.uid,
                },
            )
            return jsonify(detail="QR does not belong to logged user", reason="session_user_mismatch"), 403

        # Éxito → marcar sesión como completada y actualizar último acceso
        sess.state = "completed"
        now = now_cst()
        matched.ultimo_acceso = now
        matched.actualizado_en = now  # si existe el campo
        db.commit()

        sign_event_and_persist(db, "qr_scanned_ok", actor_uid=matched.uid, source="qr_api",
                               context={"session_id": sess.session_id})
        # Registrar login completado (para panel y auditoría)
        try:
            sign_event_and_persist(db, "login_completed", actor_uid=matched.uid, source="auth_api",
                                   context={"via": "qr", "session_id": sess.session_id})
        except Exception:
            pass
        # Emitir JWT para sesión larga en frontend
        token = create_jwt({"uid": matched.uid, "rol": matched.rol})
        return jsonify(ok=True, next="done", token=token)


@bp.post("/assign")
def assign_qr():
    """Asigna/rota un valor de QR (hash Argon2) a un usuario.

    Este endpoint es utilizado por herramientas de administración para
    aprovisionar tarjetas o códigos en producción.
    """
    data = request.get_json(force=True, silent=True) or {}
    uid = data.get("uid")
    qr_value = data.get("qr_value")
    qr_card_id = data.get("qr_card_id")

    with db_session() as db:  # type: Session
        user = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not user:
            return jsonify(detail="user not found"), 404
        reused = False
        if qr_value:
            user.qr_value_hash = hash_qr_value(qr_value)
        else:
            if not user.qr_value_hash:
                return jsonify(detail="qr_value requerido o usuario sin QR previo"), 400
            reused = True
        if qr_card_id is not None:
            user.qr_card_id = qr_card_id
        else:
            # Si no se envía y está vacío, usar el UID como identificador de tarjeta por defecto
            try:
                if not user.qr_card_id:
                    user.qr_card_id = user.uid
            except Exception:
                pass
        user.qr_status = "active"
        user.actualizado_en = now_cst()
        db.commit()
        sign_event_and_persist(db, "qr_assigned", actor_uid=user.uid, source="admin_api",
                               context={"qr_card_id": user.qr_card_id, "reused_existing": reused})
        return jsonify(ok=True, reused_existing=reused)


@bp.post("/revoke/<uid>")
def revoke_qr(uid: str):
    """Revoca el QR de un usuario (cambia estado sin borrar el hash)."""
    with db_session() as db:  # type: Session
        user = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not user:
            return jsonify(detail="user not found"), 404
        user.qr_status = "revoked"
        user.qr_revoked_at = now_cst()
        user.actualizado_en = now_cst()
        db.commit()
        sign_event_and_persist(db, "qr_revoked", actor_uid=user.uid, source="admin_api", context={})
        return jsonify(ok=True)


@bp.post("/timeout")
def qr_timeout():
    """Registrar expiración del tiempo de escaneo desde el cliente.

    El frontend avisa cuando agota su contador sin escanear. Aquí marcamos la
    sesión como expirada (si existe) y emitimos un evento amarillo estable
    (qr_session_expired) para que siempre quede en la bitácora.
    """
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify(detail="session_id required"), 400
    with db_session() as db:  # type: Session
        sess = db.query(AuthSession).filter(AuthSession.session_id == session_id).first()
        if not sess:
            return jsonify(ok=True)  # no-op
        if sess.state != "completed":
            sess.state = "expired"
            db.commit()
        sign_event_and_persist(db, "qr_session_expired", actor_uid=sess.uid, source="qr_api",
                               context={"session_id": sess.session_id, "client": True})
        return jsonify(ok=True)


# ========================
#  Fallback Universal: decodificar QR en servidor desde imagen (robusto)
#  Útil para navegadores sin BarcodeDetector o cámaras con permisos limitados.
# ========================

def _opencv_decode_try(mat_bgr):
    """Intenta varias transformaciones hasta extraer un QR y devuelve texto o None."""
    det = cv2.QRCodeDetector()

    def try_once(img):
        val, pts, _ = det.detectAndDecode(img)
        return val if val else None

    # 1) original
    v = try_once(mat_bgr)
    if v: return v

    # 2) reescalar si es enorme o muy chico
    h, w = mat_bgr.shape[:2]
    scale = 1024.0 / max(h, w)
    if scale < 1.0:
        resized = cv2.resize(mat_bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        v = try_once(resized)
        if v: return v

    # 3) gris y umbrales
    gray = cv2.cvtColor(mat_bgr, cv2.COLOR_BGR2GRAY)
    # a) adaptativo
    thr = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 31, 10)
    v = try_once(thr)
    if v: return v
    # b) Otsu
    _, thr2 = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    v = try_once(thr2)
    if v: return v

    # 4) rotaciones 90/180/270
    for rot in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE):
        rimg = cv2.rotate(mat_bgr, rot)
        v = try_once(rimg)
        if v: return v

    # 5) un poco de sharpen + intento
    k = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharp = cv2.filter2D(mat_bgr, -1, k)
    v = try_once(sharp)
    if v: return v

    return None


@bp.post("/decode")
def decode_qr_image():
    """
    multipart/form-data con campo 'image'.
    200 -> { "value": "<texto>" } si hay QR
    204 -> { "value": null } si no detecta
    400 -> { "detail": "..."} si la imagen es inválida
    """
    file = request.files.get("image")
    if not file:
        return jsonify(detail="image required"), 400

    try:
        raw = file.read()
        # Abrir con PIL (mejor compatibilidad: HEIC/WEBP/PNG/JPEG… según plugins disponibles)
        img_pil = Image.open(io.BytesIO(raw)).convert("RGB")
    except UnidentifiedImageError:
        return jsonify(detail="unsupported image format"), 400
    except Exception as e:
        return jsonify(detail=f"image read error: {e}"), 400

    # PIL -> numpy BGR para OpenCV
    try:
        mat_rgb = np.array(img_pil)
        mat_bgr = cv2.cvtColor(mat_rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        return jsonify(detail=f"image convert error: {e}"), 400

    try:
        val = _opencv_decode_try(mat_bgr)
    except Exception as e:
        return jsonify(detail=f"opencv error: {e}"), 400

    if val:
        return jsonify(value=val)
    else:
        # no encontrado
        return jsonify(value=None), 204
