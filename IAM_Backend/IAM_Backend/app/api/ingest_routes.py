from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..logging_utils import sign_event_and_persist

bp = Blueprint("ingest", __name__, url_prefix="/api/ingest")

@bp.post("/nfc_event")
def nfc_event():
    data = request.get_json(force=True, silent=True) or {}
    with db_session() as db:  # type: Session
        sign_event_and_persist(db, "nfc_event", actor_uid=None,
                               source=data.get("door_id"),
                               context={"uid_hash": data.get("uid_hash"), "result": data.get("result")})
        return jsonify(ok=True)

@bp.post("/monitoring_event")
def monitoring_event():
    data = request.get_json(force=True, silent=True) or {}
    with db_session() as db:  # type: Session
        sign_event_and_persist(db, "monitoring_event", actor_uid=None,
                               source=data.get("camera_id"),
                               context={"motion": data.get("motion"), "ts": data.get("ts")})
        return jsonify(ok=True)
