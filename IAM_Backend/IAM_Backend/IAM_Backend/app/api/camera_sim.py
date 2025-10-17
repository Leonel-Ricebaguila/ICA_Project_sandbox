from flask import Blueprint, Response, jsonify, request
from ..config import cfg
from ..db import SessionLocal
from ..models import CameraDevice
import cv2
import time

bp = Blueprint("cam_sim", __name__)

#
# Endpoints de cámaras para demo/monitorización
# - /camera_sim/<id>  → Página HTML simple de color (simula cámara)
# - /cameras          → Lista de cámaras: mezcla de env CAM_URLS + base de datos
# - /camera_mjpeg/<i> → Proxy MJPEG desde RTSP/HTTP para consumo por navegador
#   Nota: navegadores no reproducen RTSP de forma nativa; este proxy lo convierte a MJPEG.
#

COLORS = ["#aaf","#faa","#afa","#ffa","#ddd","#cdf"]

@bp.get("/camera_sim/<int:cam_id>")
def camera_sim(cam_id: int):
    color = COLORS[int(cam_id) % len(COLORS)]
    html = f"""
    <html><body style="margin:0;background:{color};height:100vh;">
      <div style="position:absolute;top:10px;left:10px;padding:6px;background:#000;color:#fff;">
        Camera {cam_id} - simulated
      </div>
    </body></html>
    """
    return Response(html, mimetype="text/html")


@bp.get("/cameras")
def list_cameras():
    """Devuelve lista simple de cámaras configuradas.
    Cada entrada es {id, name, url}.
    Configurable con env CAM_URLS="Nombre|URL,Nombre2|URL2".
    """
    cams = []
    for idx, item in enumerate(cfg.CAM_URLS, start=1):
        if "|" in item:
            name, url = item.split("|", 1)
        else:
            name, url = f"Cam {idx}", item
        url = url.strip()
        # Si es RTSP/RTMP, los navegadores no lo soportan: ofrecer proxy MJPEG
        if url.lower().startswith(("rtsp://", "rtmp://")):
            proxy_url = f"/camera_mjpeg/{idx}"
            cams.append({"id": idx, "name": name.strip(), "url": proxy_url})
        else:
            cams.append({"id": idx, "name": name.strip(), "url": url})
    # Agregar cámaras desde BD (tabla devices_cameras)
    try:
        db = SessionLocal()
        rows = db.query(CameraDevice).all()
        for r in rows:
            url = r.url.strip()
            if url.lower().startswith(("rtsp://", "rtmp://")):
                # Intentar asignar índice alto evitando colisiones visuales
                cams.append({"id": (len(cams)+1), "name": r.name, "url": f"/camera_mjpeg/{r.id}?db=1"})
            else:
                cams.append({"id": (len(cams)+1), "name": r.name, "url": url})
    finally:
        try:
            db.close()
        except Exception:
            pass
    return jsonify(cams)


def _mjpeg_generator(src_url):
    """Lee frames con OpenCV y los sirve como stream multipart/x-mixed-replace."""
    cap = cv2.VideoCapture(src_url)
    try:
        if not cap.isOpened():
            # intento reintento corto
            time.sleep(0.5)
            cap.open(src_url)
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.1)
                continue
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue
            jpg = buf.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
    finally:
        cap.release()


@bp.get("/camera_mjpeg/<int:idx>")
def camera_mjpeg(idx: int):
    """Selecciona URL desde CAM_URLS (por índice) o desde BD (?db=1) y proxea como MJPEG."""
    # Si ?db=1, obtiene desde BD por ID; de lo contrario, índice en CAM_URLS
    use_db = request.args.get('db') in ('1','true','yes')
    if use_db:
        db = SessionLocal()
        try:
            row = db.query(CameraDevice).filter(CameraDevice.id==idx).first()
            if not row:
                return Response("not found", status=404)
            url = (row.url or '').strip()
        finally:
            db.close()
    else:
        if idx <= 0 or idx > len(cfg.CAM_URLS):
            return Response("index out of range", status=404)
        item = cfg.CAM_URLS[idx-1]
        url = item.split('|',1)[1] if '|' in item else item
        url = url.strip()
    return Response(_mjpeg_generator(url), mimetype='multipart/x-mixed-replace; boundary=frame')
