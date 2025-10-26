import datetime
from typing import Union


CST = datetime.timezone(datetime.timedelta(hours=-6))  # GMT-6


def now_cst() -> datetime.datetime:
    return datetime.datetime.now(CST)


def ensure_cst(dt: Union[datetime.datetime, str, None]) -> datetime.datetime | None:
    """Return dt as timezone-aware in GMT-6. If dt is None, returns None.
    If dt is a string, tries to parse ISO8601.
    If dt is naive, assume it is in GMT-6 and attach tzinfo.
    If dt has tzinfo, convert to GMT-6.
    """
    if dt is None:
        return None
    # Parse ISO strings gracefully (including Z suffix)
    if isinstance(dt, str):
        s = dt.strip()
        try:
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            parsed = datetime.datetime.fromisoformat(s)
        except Exception:
            return None
        dt = parsed
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=CST)
    return dt.astimezone(CST)
