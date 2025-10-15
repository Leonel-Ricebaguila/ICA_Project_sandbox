"""
Versión ligera para pruebas locales (requiere modificaciones para implementación):
- Modos QR: 'otp' => payload "uid:<UID>|otp:<OTP>"
            'uid_only' => payload "uid:<UID>"
- OTP local (en memoria). No usa DB ni server.
- Cámaras: 'local' -> webcam index 0
           número  -> webcam local por índice
           URL     -> RTSP/HTTP. Si es base HTTP (p.ej. http://IP:8080) intenta /video, /video.mjpeg, /shot.jpg.
Uso: python qr.py
"""
from __future__ import annotations
import os
import time
import secrets
import re
from io import BytesIO
from typing import Optional, Dict, Tuple

# Dependencias opcionales (deben instalarse)
try:
    import qrcode
except Exception:
    qrcode = None

try:
    import cv2
except Exception:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

# Para snapshot por HTTP
try:
    import requests
except Exception:
    requests = None

# Para decodificar JPG de snapshot
try:
    import numpy as np
except Exception:
    np = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configurables
OTP_VALID_SECONDS = int(os.environ.get("OTP_VALID_SECONDS", "60"))
DEBUG = os.environ.get("DEBUG", "1") == "1"

def dprint(*args, **kw):
    if DEBUG:
        print("[DBG]", *args, **kw)

# In-memory OTP store: uid -> {"otp": int, "created": float}
current_otps: Dict[str, Dict[str, float]] = {}

# ---------------- QR / OTP helpers ----------------
def generar_otp_local(uid: str) -> Tuple[int, float]:
    """Genera un OTP de 6 dígitos y lo asocia en memoria con la uid."""
    otp = secrets.randbelow(900_000) + 100_000
    ts = time.time()
    current_otps[uid] = {"otp": int(otp), "created": ts}
    dprint("OTP generado:", otp, "para uid:", uid)
    return int(otp), ts

def otp_valido(uid: str, otp: int) -> bool:
    rec = current_otps.get(uid)
    if not rec:
        return False
    if int(rec["otp"]) != int(otp):
        return False
    return (time.time() - float(rec["created"])) <= OTP_VALID_SECONDS

def build_payload(mode: str, uid: Optional[str] = None, otp: Optional[int] = None) -> str:
    """Construye el payload del QR."""
    uid_val = uid if uid else f"anon-{secrets.token_hex(3)}"
    if mode == "otp":
        if otp is None:
            raise ValueError("otp required for mode 'otp'")
        return f"uid:{uid_val}|otp:{int(otp)}"
    elif mode == "uid_only":
        return f"uid:{uid_val}"
    else:
        raise ValueError("mode must be 'otp' or 'uid_only'")

def qr_bytes_from_payload(payload: str) -> bytes:
    """Genera PNG del QR en bytes."""
    if qrcode is None:
        raise RuntimeError("Dependencia faltante: qrcode. Instala qrcode[pil].")
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def save_qr(payload: str, path: Optional[str] = None) -> str:
    """Guarda QR en archivo PNG y devuelve la ruta."""
    if path is None:
        path = os.path.join(BASE_DIR, f"qr_{int(time.time())}.png")
    b = qr_bytes_from_payload(payload)
    with open(path, "wb") as f:
        f.write(b)
    dprint("QR guardado en", path, "payload=", payload)
    return path

# ---------------- Cámara / Escaneo (mejorado IP) ----------------
_IP_BASE_RE = re.compile(r"^https?://[^/]+(?::\d+)?/?$")  # p.ej. http://192.168.1.88:8080
COMMON_MJPEG_PATHS = ["/video", "/video.mjpeg", "/mjpeg", "/stream.mjpg", "/?action=stream"]
SNAPSHOT_PATHS     = ["/shot.jpg", "/jpeg", "/jpg", "/image.jpg", "/snapshot.jpg"]

class SnapshotStream:
    """
    Fuente compatible con VideoCapture: expone read() y release().
    Lee frames por HTTP (shot.jpg-like) haciendo polling.
    """
    def __init__(self, url: str, timeout: float = 2.5):
        if requests is None or np is None:
            raise RuntimeError("Faltan 'requests' y/o 'numpy' para SnapshotStream. pip install requests numpy")
        self.url = url
        self.timeout = timeout
        self._closed = False

    def isOpened(self):
        return not self._closed

    def read(self):
        if self._closed:
            return False, None
        try:
            r = requests.get(self.url, timeout=self.timeout)
            if r.status_code != 200:
                return False, None
            data = np.frombuffer(r.content, dtype=np.uint8)
            frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if frame is None:
                return False, None
            return True, frame
        except Exception:
            return False, None

    def release(self):
        self._closed = True

def _try_open_videocapture(url: str):
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        return cap
    # algunos backends requieren especificar FFmpeg
    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            return cap
    except Exception:
        pass
    return None

def open_capture(source: str = "local"):
    """
    'local' -> webcam 0
    dígito  -> webcam índice N
    'http(s)://...' -> intenta MJPEG en rutas comunes; si falla usa SnapshotStream (shot.jpg)
    'rtsp://...' o URL completa -> se pasa directo a OpenCV
    """
    if cv2 is None:
        print("OpenCV no instalado. Instala opencv-python.")
        return None

    # Webcam local por nombre
    if source.lower() == "local":
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        except Exception:
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        return cap

    # Webcam local por índice (string numérica)
    if source.isdigit():
        idx = int(source)
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        except Exception:
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            return None
        return cap

    # Si parece base URL sin path, probar rutas MJPEG conocidas
    if _IP_BASE_RE.match(source):
        # Preferir HTTP (https puede fallar si OpenCV no trae OpenSSL)
        if source.startswith("https://"):
            print("Aviso: si falla con HTTPS, prueba HTTP (ej. http://IP:8080).")
        for p in COMMON_MJPEG_PATHS:
            test_url = source.rstrip("/") + p
            dprint("Probando MJPEG:", test_url)
            cap = _try_open_videocapture(test_url)
            if cap is not None:
                return cap
        # Si no hay MJPEG, intentar SnapshotStream (polling de JPGs)
        for p in SNAPSHOT_PATHS:
            test_url = source.rstrip("/") + p
            dprint("Probando SNAPSHOT:", test_url)
            try:
                snap = SnapshotStream(test_url)
                ok, frame = snap.read()
                if ok and frame is not None:
                    dprint("Snapshot OK:", test_url)
                    return snap
            except Exception:
                pass
        dprint("No se pudo abrir MJPEG ni snapshot desde la base URL.")
        return None

    # Si la URL ya trae path (rtsp/http con ruta específica), intentar directo
    cap = _try_open_videocapture(source)
    if cap is not None:
        return cap

    # Último recurso: si es HTTP(s) y podría ser imagen directa
    if source.startswith("http"):
        try:
            snap = SnapshotStream(source)
            ok, frame = snap.read()
            if ok and frame is not None:
                return snap
        except Exception:
            pass

    dprint("No se pudo abrir la fuente de video:", source)
    return None

def scan_qr_camera(timeout: int = 60, source: str = "local") -> Optional[str]:
    """
    Abre la cámara y busca el primer QR detectado.
    Retorna el payload (string) o None si timeout/error.
    """
    cap = open_capture(source)
    if cap is None:
        return None

    detector = None
    try:
        if hasattr(cv2, "QRCodeDetector"):
            detector = cv2.QRCodeDetector()
    except Exception:
        detector = None

    start = time.time()
    payload = None
    try:
        while time.time() - start < timeout:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.02)
                continue

            # intentar pyzbar (más robusto)
            if zbar_decode is not None:
                try:
                    decs = zbar_decode(frame)
                    if decs:
                        payload = decs[0].data.decode("utf-8", errors="ignore").strip()
                        dprint("pyzbar detectó:", payload)
                        break
                except Exception:
                    pass

            # fallback OpenCV
            if detector is not None:
                try:
                    data, _, _ = detector.detectAndDecode(frame)
                    if data and data.strip():
                        payload = data.strip()
                        dprint("cv2 detectó:", payload)
                        break
                except Exception:
                    pass

            # pequeña pausa
            time.sleep(0.02)
    finally:
        cap.release()
    return payload

def parse_payload(payload: str) -> Dict[str, str]:
    """Parsea payload tipo 'uid:...|otp:...' o 'uid:...'."""
    res = {}
    try:
        parts = payload.split("|")
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                res[k.strip()] = v.strip()
    except Exception:
        pass
    return res

# ---------------- Flujos de alto nivel ----------------
def crear_qr_mode(mode: str, uid: Optional[str] = None, guardar: bool = True) -> Tuple[str, Optional[int]]:
    """
    Crea QR según mode:
      - 'otp': requiere uid; genera OTP local y retorna (ruta_png, otp)
      - 'uid_only': uid opcional; retorna (ruta_png, None)
    """
    if mode not in ("otp", "uid_only"):
        raise ValueError("mode must be 'otp' or 'uid_only'")

    if mode == "otp":
        if not uid:
            raise ValueError("uid requerido para mode 'otp'")
        otp, _ = generar_otp_local(uid)
        payload = build_payload("otp", uid=uid, otp=otp)
    else:
        uid_val = uid if uid else None
        payload = build_payload("uid_only", uid=uid_val)
        otp = None

    path = save_qr(payload) if guardar else "<in-memory>"
    return path, otp

def escanear_y_validar(camera_source: str = "local", timeout: int = 60) -> Tuple[bool, str]:
    """
    Escanea QR desde la cámara indicada y valida localmente:
      - si payload contiene uid+otp => comprueba otp (local)
      - si payload contiene solo uid => acepta (prueba local)
    """
    payload = scan_qr_camera(timeout=timeout, source=camera_source)
    if not payload:
        return False, "No se detectó QR (timeout o error cámara)."

    parsed = parse_payload(payload)
    dprint("Payload parseado:", parsed)
    uid = parsed.get("uid")
    otp = parsed.get("otp")

    if not uid:
        return False, "QR inválido: falta uid."

    if otp is None:
        # modo uid_only -> dado que no hay DB en esta prueba, lo aceptamos localmente
        return True, f"UID '{uid}' detectada (modo uid_only)."
    else:
        try:
            otp_i = int(otp)
        except Exception:
            return False, "OTP en QR no es numérico."
        if otp_valido(uid, otp_i):
            return True, f"UID '{uid}' + OTP válido."
        else:
            return False, "OTP inválido o expirado."

# ---------------- CLI sencillo ----------------
def cli():
    print("=== verificacion_2fa_encryption (modo local) ===")
    while True:
        print("\nOpciones:")
        print("1) Crear QR (modo 'otp') -> requiere UID (OTP local)")
        print("2) Crear QR (modo 'uid_only') -> UID opcional")
        print("3) Escanear QR con cámara (local / índice / URL IP) y validar")
        print("4) Salir")
        opt = input("Elige: ").strip()
        if opt == "1":
            uid = input("UID (string): ").strip()
            if not uid:
                print("UID requerido.")
                continue
            path, otp = crear_qr_mode("otp", uid=uid, guardar=True)
            print(f"QR (otp) creado en: {path}")
            print(f"OTP generado (local): {otp} (válido {OTP_VALID_SECONDS}s)")
        elif opt == "2":
            uid = input("UID (opcional, enter para anon): ").strip() or None
            path, _ = crear_qr_mode("uid_only", uid=uid, guardar=True)
            print("QR (uid_only) creado en:", path)
        elif opt == "3":
            print("Introduce la fuente de cámara:")
            print(" - 'local' para webcam por defecto")
            print(" - número (0,1,2,...) para una webcam específica")
            print(" - URL RTSP/HTTP para cámara IP (p.ej. rtsp://..., http://IP:8080 o http://IP:8080/video)")
            src = input("Fuente [local]: ").strip() or "local"
            timeout = input(f"Timeout seg (default {OTP_VALID_SECONDS+10}): ").strip()
            try:
                t = int(timeout) if timeout else (OTP_VALID_SECONDS + 10)
            except Exception:
                t = OTP_VALID_SECONDS + 10
            print("Abriendo cámara... apunta el QR a la cámara")
            ok, msg = escanear_y_validar(camera_source=src, timeout=t)
            if ok:
                print("ACCESO CONCEDIDO ->", msg)
            else:
                print("ACCESO DENEGADO ->", msg)
        elif opt == "4":
            print("Saliendo.")
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    cli()
