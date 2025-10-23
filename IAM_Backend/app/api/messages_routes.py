from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import db_session
from ..models import Mensaje, Usuario, MessageRead, ChannelKey
from ..logging_utils import sign_event_and_persist

bp = Blueprint("messages", __name__, url_prefix="/api/messages")

ALLOWED_GROUPS = {"IAM", "IM", "AC", "Mon", "Avisos"}

def _group_allowed_for_role(group: str, role: str, read: bool) -> bool:
    # Avisos: lectura para todos; escritura solo admin
    if group == "Avisos":
        return True if read else (role == 'R-ADM')
    if group == "IAM":
        return role == 'R-ADM'
    if group == "IM":
        return role in ('R-IM', 'R-ADM')
    if group == "AC":
        return role in ('R-AC', 'R-ADM')
    if group == "Mon":
        return role in ('R-MON', 'R-ADM')
    return False

def _is_dm(grupo: str) -> bool:
    return isinstance(grupo, str) and grupo.upper().startswith('DM:')

def _dm_participants(grupo: str) -> list[str]:
    try:
        parts = grupo.split(':')[1:]
        return [p for p in parts if p]
    except Exception:
        return []

@bp.get("")
def list_messages():
    grupo = request.args.get("grupo")
    requester = request.args.get("uid")
    limit = request.args.get("limit", type=int) or 100
    with db_session() as db:  # type: Session
        if not grupo:
            return jsonify(detail="grupo required"), 400
        # Autorización básica por grupo/DM
        if _is_dm(grupo):
            if not requester:
                return jsonify(detail="uid required"), 400
            parts = _dm_participants(grupo)
            if requester not in parts:
                return jsonify(detail="forbidden"), 403
        else:
            if grupo not in ALLOWED_GROUPS:
                return jsonify(detail="grupo inválido"), 400
            if not requester:
                return jsonify(detail="uid required"), 400
            u = db.query(Usuario).filter(Usuario.uid == requester).first()
            if not u or u.estado != 'active':
                return jsonify(detail="uid inválido"), 403
            if not _group_allowed_for_role(grupo, u.rol, read=True):
                return jsonify(detail="forbidden"), 403
        q = db.query(Mensaje).order_by(Mensaje.creado_en.desc())
        if grupo:
            q = q.filter(Mensaje.grupo == grupo)
        rows = q.limit(limit).all()
        # Mapear usuarios para nombres
        uids: set[str] = set()
        for r in rows:
            if r.remitente_uid:
                uids.add(r.remitente_uid)
        # Lecturas por mensaje
        reads_by_msg: dict[int, list[MessageRead]] = {}
        if rows:
            msg_ids = [r.msg_id for r in rows]
            rds = db.query(MessageRead).filter(MessageRead.msg_id.in_(msg_ids)).all()
            for rd in rds:
                reads_by_msg.setdefault(rd.msg_id, []).append(rd)
                uids.add(rd.uid)
        umap = {u.uid: u for u in db.query(Usuario).filter(Usuario.uid.in_(list(uids))).all()}
        def fmt_ts(ts):
            try:
                s = ts.isoformat()
                if "." in s:
                    s = s.split(".")[0]
                return s
            except Exception:
                return None
        out = []
        for r in rows:
            ru = umap.get(r.remitente_uid)
            recs = reads_by_msg.get(r.msg_id, [])
            out.append({
                "msg_id": r.msg_id,
                "remitente_uid": r.remitente_uid,
                "remitente_nombre": getattr(ru, 'nombre', None),
                "remitente_apellido": getattr(ru, 'apellido', None),
                "grupo": r.grupo,
                "contenido": r.contenido,
                "creado_en": fmt_ts(r.creado_en) if getattr(r, 'creado_en', None) else None,
                "leido_por": [
                    {
                        "uid": rd.uid,
                        "nombre": getattr(umap.get(rd.uid), 'nombre', None),
                        "apellido": getattr(umap.get(rd.uid), 'apellido', None),
                        "read_at": fmt_ts(getattr(rd, 'read_at', None)) if getattr(rd, 'read_at', None) else None,
                    }
                    for rd in recs
                ],
            })
        return jsonify(out)

@bp.post("")
def create_message():
    data = request.get_json(force=True, silent=True) or {}
    remitente_uid = data.get("remitente_uid")
    grupo = data.get("grupo")
    contenido = data.get("contenido")
    if not contenido:
        return jsonify(detail="contenido required"), 400
    with db_session() as db:  # type: Session
        # Restringir auditor (R-AUD) a solo lectura: no puede publicar
        if remitente_uid:
            u = db.query(Usuario).filter(Usuario.uid == remitente_uid).first()
            if not u or u.estado != 'active':
                return jsonify(detail="remitente inválido"), 400
            if u.rol == 'R-AUD':
                return jsonify(detail="forbidden"), 403
        # Validación de destino (grupo fijo o DM)
        if not grupo:
            return jsonify(detail="grupo required"), 400
        # DM: formato DM:uid1:uid2 (uids ordenados en cliente).
        if _is_dm(grupo):
            parts = _dm_participants(grupo)
            if not remitente_uid or remitente_uid not in parts:
                return jsonify(detail="forbidden"), 403
        else:
            if grupo not in ALLOWED_GROUPS:
                return jsonify(detail="grupo inválido"), 400
            # Sólo roles permitidos pueden escribir; Avisos solo admin
            if remitente_uid:
                if not _group_allowed_for_role(grupo, u.rol, read=False):
                    return jsonify(detail="forbidden"), 403
        m = Mensaje(remitente_uid=remitente_uid, grupo=grupo, contenido=contenido)
        db.add(m)
        db.commit()
        db.refresh(m)
        try:
            sign_event_and_persist(
                db,
                event_name='message_created',
                actor_uid=remitente_uid,
                source='api/messages',
                context={
                    'msg_id': m.msg_id,
                    'grupo': grupo,
                    # No registrar contenido; puede estar cifrado E2E
                    'len': len(contenido or ''),
                }
            )
        except Exception:
            pass
        return jsonify(msg_id=m.msg_id), 201

@bp.get("/summary")
def summary():
    """Resumen de mensajes por canal para sidebar: último mensaje + no leídos.
    - groups: solo los grupos permitidos por el rol del solicitante
    - dm_unread: total de DMs no leídos para el solicitante
    """
    requester = request.args.get("uid")
    if not requester:
        return jsonify(detail="uid required"), 400
    with db_session() as db:  # type: Session
        u = db.query(Usuario).filter(Usuario.uid == requester, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        groups_allowed = []
        for g in sorted(ALLOWED_GROUPS):
            if _group_allowed_for_role(g, u.rol, read=True):
                groups_allowed.append(g)
        def fmt_ts(ts):
            try:
                s = ts.isoformat()
                if "." in s:
                    s = s.split(".")[0]
                return s
            except Exception:
                return None
        out_groups = []
        for g in groups_allowed:
            last = db.query(Mensaje).filter(Mensaje.grupo == g).order_by(Mensaje.creado_en.desc()).first()
            # contar no leídos (excluye propios)
            unread = 0
            try:
                unread = (
                    db.query(Mensaje)
                    .outerjoin(MessageRead, (MessageRead.msg_id == Mensaje.msg_id) & (MessageRead.uid == requester))
                    .filter(Mensaje.grupo == g, Mensaje.remitente_uid != requester, MessageRead.id.is_(None))
                    .count()
                )
            except Exception:
                unread = 0
            if last:
                lu = db.query(Usuario).filter(Usuario.uid == last.remitente_uid).first() if last.remitente_uid else None
                out_groups.append({
                    "grupo": g,
                    "unread": unread,
                    "last": {
                        "msg_id": last.msg_id,
                        "remitente_uid": last.remitente_uid,
                        "remitente_nombre": getattr(lu, 'nombre', None),
                        "remitente_apellido": getattr(lu, 'apellido', None),
                        "contenido": last.contenido,
                        "creado_en": fmt_ts(getattr(last, 'creado_en', None)) if getattr(last, 'creado_en', None) else None,
                    }
                })
            else:
                out_groups.append({"grupo": g, "unread": unread, "last": None})

        # DMs: total de no leídos
        try:
            dm_unread = (
                db.query(Mensaje)
                .filter(Mensaje.grupo.like('DM:%'))
                .outerjoin(MessageRead, (MessageRead.msg_id == Mensaje.msg_id) & (MessageRead.uid == requester))
                .filter(MessageRead.id.is_(None), Mensaje.remitente_uid != requester)
                .filter(Mensaje.grupo.like(f'%:{requester}') | Mensaje.grupo.like(f'DM:{requester}:%'))
                .count()
            )
        except Exception:
            # Fallback por si el OR con like no es soportado igual
            all_dm = db.query(Mensaje).filter(Mensaje.grupo.like('DM:%')).all()
            dm_unread = 0
            for m in all_dm:
                parts = _dm_participants(m.grupo)
                if requester in parts and m.remitente_uid != requester:
                    r = db.query(MessageRead).filter(MessageRead.msg_id == m.msg_id, MessageRead.uid == requester).first()
                    if not r:
                        dm_unread += 1
        return jsonify({"groups": out_groups, "dm_unread": int(dm_unread)})

@bp.post("/read")
def mark_read():
    data = request.get_json(force=True, silent=True) or {}
    msg_id = data.get("msg_id", None)
    uid = data.get("uid", None)
    if not msg_id or not uid:
        return jsonify(detail="msg_id, uid required"), 400
    with db_session() as db:  # type: Session
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        m = db.query(Mensaje).filter(Mensaje.msg_id == msg_id).first()
        if not m:
            return jsonify(detail="not found"), 404
        # Autorización de lectura igual que en list_messages
        if _is_dm(m.grupo):
            if uid not in _dm_participants(m.grupo):
                return jsonify(detail="forbidden"), 403
        else:
            if m.grupo not in ALLOWED_GROUPS:
                return jsonify(detail="grupo inválido"), 400
            if not _group_allowed_for_role(m.grupo, u.rol, read=True):
                return jsonify(detail="forbidden"), 403
        existing = db.query(MessageRead).filter(MessageRead.msg_id == msg_id, MessageRead.uid == uid).first()
        if existing:
            return jsonify(ok=True)
        db.add(MessageRead(msg_id=msg_id, uid=uid))
        db.commit()
        return jsonify(ok=True)

@bp.post("/backfill_self")
def backfill_self_part():
    """Permite al remitente agregar su propia 'part' en mensajes de grupo antiguos.
    Body: {msg_id, uid, part}
    Solo si:
      - el usuario está activo
      - el usuario es el remitente del mensaje
      - el mensaje es de un grupo (no DM)
    """
    data = request.get_json(force=True, silent=True) or {}
    msg_id = data.get("msg_id")
    uid = data.get("uid")
    part = data.get("part")
    if not msg_id or not uid or not part:
        return jsonify(detail="msg_id, uid, part required"), 400
    with db_session() as db:  # type: Session
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        m = db.query(Mensaje).filter(Mensaje.msg_id == msg_id).first()
        if not m:
            return jsonify(detail="not found"), 404
        if _is_dm(m.grupo):
            return jsonify(detail="invalid target"), 400
        if m.remitente_uid != uid:
            return jsonify(detail="forbidden"), 403
        # Intentar parsear JSON moderno {__gm__:true, from:..., parts:{}}
        import json
        try:
            obj = json.loads(m.contenido or "")
        except Exception:
            obj = None
        if not isinstance(obj, dict) or not obj.get("__gm__"):
            # Convertir legado a formato moderno con solo la nueva parte del remitente
            obj = {"__gm__": True, "from": m.remitente_uid, "parts": {}}
        parts = obj.get("parts") if isinstance(obj.get("parts"), dict) else {}
        if parts.get(uid) == part:
            return jsonify(ok=True)
        parts[uid] = part
        obj["parts"] = parts
        try:
            m.contenido = json.dumps(obj, ensure_ascii=False)
            db.add(m)
            db.commit()
        except Exception:
            db.rollback()
            return jsonify(detail="update failed"), 500
        return jsonify(ok=True)

@bp.post("/backfill_parts")
def backfill_parts():
    """Permite al REMITENTE agregar/actualizar 'parts' para destinatarios con devkey disponible.
    Body: {msg_id, uid, parts: {uid: ciphertext, ...}}
    Reglas:
      - uid activo
      - uid es remitente del mensaje
      - mensaje es de grupo (no DM)
    """
    data = request.get_json(force=True, silent=True) or {}
    msg_id = data.get("msg_id")
    uid = data.get("uid")
    parts_in = data.get("parts") or {}
    if not msg_id or not uid or not isinstance(parts_in, dict):
        return jsonify(detail="msg_id, uid, parts required"), 400
    with db_session() as db:  # type: Session
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        m = db.query(Mensaje).filter(Mensaje.msg_id == msg_id).first()
        if not m:
            return jsonify(detail="not found"), 404
        if _is_dm(m.grupo):
            return jsonify(detail="invalid target"), 400
        if m.remitente_uid != uid:
            return jsonify(detail="forbidden"), 403
        import json
        try:
            obj = json.loads(m.contenido or "")
        except Exception:
            obj = None
        if not isinstance(obj, dict) or not obj.get("__gm__"):
            obj = {"__gm__": True, "from": m.remitente_uid, "parts": {}}
        parts = obj.get("parts") if isinstance(obj.get("parts"), dict) else {}
        changed = False
        for k,v in parts_in.items():
            if not v:
                continue
            if parts.get(k) != v:
                parts[k] = v
                changed = True
        if not changed:
            return jsonify(ok=True)
        obj["parts"] = parts
        try:
            m.contenido = json.dumps(obj, ensure_ascii=False)
            db.add(m)
            db.commit()
        except Exception:
            db.rollback()
            return jsonify(detail="update failed"), 500
        return jsonify(ok=True)

# ------------ Canal Keys (chat symmetric keys) ------------
@bp.get("/chan_key")
def get_chan_key():
    channel = request.args.get("channel")
    uid = request.args.get("uid")
    if not channel or not uid:
        return jsonify(detail="channel, uid required"), 400
    with db_session() as db:
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        # Autorización de lectura del canal
        if _is_dm(channel):
            if uid not in _dm_participants(channel):
                return jsonify(detail="forbidden"), 403
        else:
            if channel not in ALLOWED_GROUPS:
                return jsonify(detail="invalid channel"), 400
            if not _group_allowed_for_role(channel, u.rol, read=True):
                return jsonify(detail="forbidden"), 403
        ck = db.query(ChannelKey).filter(ChannelKey.channel == channel).first()
        cipher = None
        if ck and isinstance(ck.key_map, dict):
            cipher = ck.key_map.get(uid)
        return jsonify({"exists": bool(ck), "cipher": cipher})

@bp.post("/chan_key")
def put_chan_key():
    data = request.get_json(force=True, silent=True) or {}
    channel = data.get("channel")
    uid = data.get("uid")
    cipher = data.get("cipher")
    if not channel or not uid or not cipher:
        return jsonify(detail="channel, uid, cipher required"), 400
    with db_session() as db:
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        # Autorización: el usuario solo puede escribir su entrada
        if _is_dm(channel):
            if uid not in _dm_participants(channel):
                return jsonify(detail="forbidden"), 403
        else:
            if channel not in ALLOWED_GROUPS:
                return jsonify(detail="invalid channel"), 400
            if not _group_allowed_for_role(channel, u.rol, read=True):
                return jsonify(detail="forbidden"), 403
        ck = db.query(ChannelKey).filter(ChannelKey.channel == channel).first()
        if not ck:
            ck = ChannelKey(channel=channel, key_map={uid: cipher})
            db.add(ck)
        else:
            m = dict(ck.key_map or {})
            m[uid] = cipher
            ck.key_map = m
            db.add(ck)
        db.commit()
        return jsonify(ok=True)

@bp.post("/chan_key/batch")
def put_chan_key_batch():
    data = request.get_json(force=True, silent=True) or {}
    channel = data.get("channel")
    uid = data.get("uid")
    wraps = data.get("wraps") or {}
    if not channel or not uid or not isinstance(wraps, dict):
        return jsonify(detail="channel, uid, wraps required"), 400
    with db_session() as db:
        u = db.query(Usuario).filter(Usuario.uid == uid, Usuario.estado=='active').first()
        if not u:
            return jsonify(detail="forbidden"), 403
        if _is_dm(channel):
            if uid not in _dm_participants(channel):
                return jsonify(detail="forbidden"), 403
        else:
            if channel not in ALLOWED_GROUPS:
                return jsonify(detail="invalid channel"), 400
            if not _group_allowed_for_role(channel, u.rol, read=True):
                return jsonify(detail="forbidden"), 403
        ck = db.query(ChannelKey).filter(ChannelKey.channel == channel).first()
        if not ck:
            ck = ChannelKey(channel=channel, key_map={})
            db.add(ck)
        m = dict(ck.key_map or {})
        # El escritor puede proponer envoltorios para otros uid miembros; los mergeamos.
        for k, v in wraps.items():
            if v:
                m[k] = v
        ck.key_map = m
        db.add(ck)
        db.commit()
        return jsonify(ok=True)
