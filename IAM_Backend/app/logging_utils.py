import os, json, binascii
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from .config import cfg
from .db import SessionLocal
from .models import Evento
from sqlalchemy import desc
import hashlib

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

def sign_event_and_persist(db, event_name, actor_uid=None, source=None, context=None):
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
    return ev
