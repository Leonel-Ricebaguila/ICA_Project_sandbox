from flask import Blueprint, jsonify

bp = Blueprint("nfc_sim", __name__)

@bp.get("/nfc_sim/read_ok/<door_id>")
def nfc_ok(door_id: str):
    return jsonify(uid_hash="SIMULATED_HASH_ABC123", door_id=door_id, result="ok")

@bp.get("/nfc_sim/read_fail/<door_id>")
def nfc_fail(door_id: str):
    return jsonify(uid_hash="SIMULATED_HASH_XYZ", door_id=door_id, result="denied")
