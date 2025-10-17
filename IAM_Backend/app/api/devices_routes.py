from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import CameraDevice, QRScannerDevice, NFCDevice
import ipaddress, datetime

bp = Blueprint("devices", __name__, url_prefix="/api/dev")


class DB:
    def __enter__(self):
        self.db: Session = SessionLocal(); return self.db
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None: self.db.commit()
        else: self.db.rollback()
        self.db.close()


def _as_dict_cam(c: CameraDevice):
    return {"id": c.id, "name": c.name, "ip": c.ip, "url": c.url,
            "status": c.status, "location": c.location,
            "last_seen": c.last_seen.isoformat() if c.last_seen else None}


@bp.get("/cameras")
def list_cams():
    with DB() as db:
        rows = db.query(CameraDevice).all()
        return jsonify([_as_dict_cam(x) for x in rows])


@bp.post("/cameras")
def add_cam():
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        c = CameraDevice(name=data.get("name","Cam"), ip=data.get("ip"), url=data.get("url",""),
                         status=data.get("status","active"), location=data.get("location"))
        db.add(c); db.flush()
        return jsonify(id=c.id)


@bp.put("/cameras/<int:cid>")
def upd_cam(cid:int):
    data = request.get_json(force=True, silent=True) or {}
    with DB() as db:
        c = db.query(CameraDevice).filter(CameraDevice.id==cid).first()
        if not c: return jsonify(detail="not found"), 404
        for k in ("name","ip","url","status","location"):
            if k in data: setattr(c,k,data[k])
        c.last_seen = datetime.datetime.utcnow()
        return jsonify(ok=True)


@bp.get("/scan")
def scan_network():
    """Escaneo simple HTTP para cámaras.
    Params: cidr=192.168.1.0/24, port=8080, path=/video, save=0
    Devuelve lista de {ip, url} detectados.
    """
    cidr = request.args.get("cidr")
    port = int(request.args.get("port", "8080"))
    path = request.args.get("path", "/video")
    save = request.args.get("save") in ("1","true","yes")
    if not cidr:
        return jsonify(detail="cidr required"), 400

    # Lazy import to avoid hard dependency at startup
    try:
        import requests  # type: ignore
    except Exception:
        return jsonify(detail="requests not installed; install to use /api/dev/scan"), 501

    net = ipaddress.ip_network(cidr, strict=False)
    found = []
    for ip in net.hosts():
        url = f"http://{ip}:{port}{path}"
        try:
            r = requests.get(url, timeout=0.7, stream=True)
            ct = r.headers.get("Content-Type","")
            if r.status_code==200 and ("multipart" in ct or "jpeg" in ct or r.raw):
                found.append({"ip": str(ip), "url": url})
        except Exception:
            pass

    if save and found:
        with DB() as db:
            for f in found:
                name = f"Cam {f['ip']}"
                if not db.query(CameraDevice).filter(CameraDevice.url==f['url']).first():
                    db.add(CameraDevice(name=name, ip=f['ip'], url=f['url']))
    return jsonify(found)
