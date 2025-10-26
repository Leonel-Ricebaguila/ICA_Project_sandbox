from typing import Optional, Tuple, List
from flask import request
from sqlalchemy.orm import Session
from .auth import verify_jwt
from .models import Usuario


def current_identity(db: Session, allow_query: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Obtiene (uid, rol) de la petición.

    - Por defecto SOLO acepta Authorization: Bearer <JWT>.
    - Si allow_query=True, como compatibilidad acepta ?uid= para endpoints
      específicos (p. ej., fases de transición de frontend).
    """
    authz = request.headers.get("Authorization", "").strip()
    if authz.lower().startswith("bearer "):
        token = authz.split(" ", 1)[1].strip()
        try:
            payload = verify_jwt(token)
            uid = payload.get("uid")
            if uid:
                u = db.query(Usuario).filter(Usuario.uid == uid).first()
                if u and u.estado == "active":
                    return (u.uid, u.rol)
        except Exception:
            pass
    if allow_query:
        uid = request.args.get("uid")
        if uid:
            u = db.query(Usuario).filter(Usuario.uid == uid).first()
            if u and u.estado == "active":
                return (u.uid, u.rol)
    return (None, None)


def require_roles(db: Session, roles: List[str]) -> Tuple[Optional[str], Optional[Tuple[str, int]]]:
    """Valida que el requester pertenezca a alguno de los roles dados (JWT requerido)."""
    uid, role = current_identity(db, allow_query=False)
    if not uid:
        return None, ("unauthorized", 401)
    if role not in roles:
        return None, ("forbidden", 403)
    return uid, None
