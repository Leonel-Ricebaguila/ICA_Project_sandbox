import time
from typing import Tuple, Dict

# Intentos fallidos y bloqueo temporal (en memoria de proceso)
LOCK_WINDOW_SEC = 10 * 60  # 10 minutos
MAX_ATTEMPTS = 3

_attempts: Dict[str, Dict[str, int]] = {}


def check_lock(key: str) -> int:
    """Devuelve segundos restantes de bloqueo (>0) o 0 si no hay bloqueo."""
    rec = _attempts.get(key)
    now_ts = int(time.time())
    if rec and rec.get("locked_until", 0) > now_ts:
        return rec["locked_until"] - now_ts
    return 0


def register_failure(key: str) -> Tuple[int, int]:
    """Incrementa contador y devuelve (count, locked_until_ts)."""
    now_ts = int(time.time())
    rec = _attempts.get(key) or {"count": 0, "first_ts": now_ts, "locked_until": 0}
    rec["count"] = int(rec.get("count", 0)) + 1
    if rec["count"] >= MAX_ATTEMPTS:
        rec["locked_until"] = now_ts + LOCK_WINDOW_SEC
    _attempts[key] = rec
    return rec["count"], rec["locked_until"]


def reset(key: str) -> None:
    _attempts.pop(key, None)

