from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import Evento
from ..access import log_access
from sqlalchemy import desc

bp = Blueprint("access", __name__, url_prefix="/api/access_log")


@bp.post("")
def ingest_access():
    data = request.get_json(force=True, silent=True) or {}
    actor_uid = data.get("actor_uid")
    result = data.get("result")  # granted/denied/attempt
    source = data.get("source")
    device_id = data.get("device_id")
    camera_id = data.get("camera_id")
    area = data.get("area")
    reason = data.get("reason")
    extra = data.get("extra") or {}
    if result not in {"granted", "denied", "attempt"}:
        return jsonify(detail="invalid result"), 400
    ev = log_access(actor_uid, result, source=source, device_id=device_id, camera_id=camera_id, area=area, reason=reason, extra=extra)
    return jsonify(id=ev.id, event=ev.event)


@bp.get("")
def list_access():
    limit = request.args.get("limit", type=int) or 100
    actor_uid = request.args.get("actor_uid")
    result = request.args.get("result")  # optional: granted/denied/attempt
    with db_session() as db:  # type: Session
        q = db.query(Evento).order_by(desc(Evento.ts))
        q = q.filter(Evento.event.in_(["access_granted", "access_denied", "access_attempt"]))
        if actor_uid:
            q = q.filter(Evento.actor_uid == actor_uid)
        rows = q.limit(limit).all()
        out = []
        for r in rows:
            ctx = r.context or {}
            if result and ctx.get("result") != result:
                continue
            out.append({
                "id": r.id,
                "event": r.event,
                "actor_uid": r.actor_uid,
                "source": r.source,
                "context": ctx,
                "ts": r.ts.isoformat() if getattr(r, "ts", None) else None,
            })
        return jsonify(out)

