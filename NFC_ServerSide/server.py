#!/usr/bin/env python3
"""
Flask server that exposes endpoints to manage NFC UIDs and roles.

Environment variables:
- NFC_DB_PATH: path to SQLite database file (default: ./data.db)
- HOST: bind host (default: 0.0.0.0)
- PORT: port number (default: 8080)
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict

from flask import Flask, jsonify, request

import db as db_utils


app = Flask(__name__)


def _parse_role(value: Any) -> int:
    try:
        return int(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("role must be an integer") from exc


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/cards")
def list_cards():
    records = db_utils.list_cards()
    return jsonify([asdict(r) for r in records])


@app.get("/cards/<uid>")
def get_card(uid: str):
    record = db_utils.get_card(uid)
    if not record:
        return jsonify({"error": "not found"}), 404
    return jsonify(asdict(record))


@app.post("/cards")
def upsert_card():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    uid = (payload.get("uid") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    try:
        role = _parse_role(payload.get("role"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    note = (payload.get("note") or "").strip()
    db_utils.upsert_card(uid=uid, role=role, note=note)
    return jsonify({"status": "ok"})


@app.delete("/cards/<uid>")
def delete_card(uid: str):
    removed = db_utils.delete_card(uid)
    if not removed:
        return jsonify({"error": "not found"}), 404
    return jsonify({"status": "deleted"})


@app.get("/lookup/<uid>")
def lookup(uid: str):
    record = db_utils.get_card(uid)
    if not record:
        return jsonify({"uid": uid, "allowed": False, "role": None})
    return jsonify({"uid": record.uid, "allowed": True, "role": record.role})


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    db_utils.initialize_database()
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()


