from typing import Optional, Dict, Any
from .db import db_session
from .logging_utils import sign_event_and_persist


def log_access(
    actor_uid: Optional[str],
    result: str,
    source: Optional[str] = None,
    device_id: Optional[int] = None,
    camera_id: Optional[int] = None,
    area: Optional[str] = None,
    reason: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Registra un evento de acceso en la bitácora (tabla Evento) con firma y hash en cadena.
    - result: "granted" | "denied" | "attempt"
    - source: origen (p.ej. "qr_scanner", "nfc_reader", "device:<id>")
    """
    event_map = {
        "granted": "access_granted",
        "denied": "access_denied",
        "attempt": "access_attempt",
    }
    ev_name = event_map.get(result, "access_attempt")
    ctx = {
        "result": result,
        "device_id": device_id,
        "camera_id": camera_id,
        "area": area,
        "reason": reason,
    }
    if extra:
        ctx.update(extra)
    with db_session() as db:
        return sign_event_and_persist(db, ev_name, actor_uid=actor_uid, source=source, context=ctx)

