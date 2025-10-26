import os, json, binascii
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from .config import cfg
from .db import SessionLocal
from .models import Evento
from sqlalchemy import desc
import hashlib
from threading import Lock
from queue import Queue

SIGNING_KEY_PATH = "./ed25519_secret.hex"

def load_or_create_signing_key():
    if cfg.ED25519_SECRET_HEX:
        return SigningKey(binascii.unhexlify(cfg.ED25519_SECRET_HEX))
    if os.path.exists(SIGNING_KEY_PATH):
        with open(SIGNING_KEY_PATH, "r") as f:
            sk_hex = f.read().strip()
        return SigningKey(binascii.unhexlify(sk_hex))
    sk = SigningKey.generate()
    sk_hex = binascii.hexlify(sk.encode()).decode()
    with open(SIGNING_KEY_PATH, "w") as f:
        f.write(sk_hex)
    return sk

_signing_key = load_or_create_signing_key()

def last_hash_prev(db):
    ev = db.query(Evento).order_by(desc(Evento.id)).first()
    return ev.hash_prev if ev else None

_listeners: list[Queue] = []
_ls_lock = Lock()

def register_log_listener() -> Queue:
    q: Queue = Queue(maxsize=1000)
    with _ls_lock:
        # Límite: si excede, expulsar el más antiguo
        if len(_listeners) >= getattr(cfg, 'MAX_SSE_LISTENERS', 100):
            try:
                _listeners.pop(0)
            except Exception:
                _listeners.clear()
        _listeners.append(q)
    return q

def unregister_log_listener(q: Queue) -> None:
    with _ls_lock:
        try:
            _listeners.remove(q)
        except ValueError:
            pass

def _broadcast_event(payload: dict) -> None:
    with _ls_lock:
        sinks = list(_listeners)
    for q in sinks:
        try:
            q.put_nowait(payload)
        except Exception:
            # if queue full or closed, drop silently
            pass

def _sanitize_context(ctx):
    try:
        if not isinstance(ctx, dict):
            return ctx
        out = dict(ctx)
        sid = out.get("session_id")
        if isinstance(sid, str) and len(sid) >= 6:
            out["session_id"] = "***" + sid[-6:]
        return out
    except Exception:
        return ctx


def sign_event_and_persist(db, event_name, actor_uid=None, source=None, context=None):
    context = _sanitize_context(context)
    payload = {
        "event": event_name,
        "actor_uid": actor_uid,
        "source": source,
        "context": context or {}
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    sig = _signing_key.sign(payload_bytes).signature
    sig_b64 = binascii.b2a_base64(sig).decode().strip()
    prev = last_hash_prev(db)
    # compute simple chain hash: H(prev || payload || sig)
    m = hashlib.sha256()
    if prev:
        m.update(prev.encode())
    m.update(payload_bytes)
    m.update(sig)
    hash_prev = m.hexdigest()
    ev = Evento(event=event_name, actor_uid=actor_uid, source=source, context=context, signature=sig_b64, hash_prev=hash_prev)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    try:
        _broadcast_event({
            "id": ev.id,
            "event": event_name,
            "actor_uid": actor_uid,
            "source": source,
            "ts": getattr(ev, 'ts', None).isoformat() if getattr(ev, 'ts', None) else None,
            "context": context or {},
        })
    except Exception:
        pass
    return ev
