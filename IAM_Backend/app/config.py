import os

class Config:
    # --------- JWT / App secret ----------
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme_replace_with_random_32b")
    JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
    # --------- Base de datos ----------
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iam.db")

    # --------- Parámetros de QR ----------
    QR_TTL_SECONDS = int(os.getenv("QR_TTL_SECONDS", "60"))  # ventana de 60 s
    QR_BYTES = int(os.getenv("QR_BYTES", "20"))              # longitud del valor Base32

    # --------- Seguridad de red (ACL de IPs permitidas) ----------
    # Formato CIDR separados por coma. Ejemplo:
    #   "127.0.0.1/32,192.168.1.0/24"
    ALLOWED_IP_RANGES = [
        cidr.strip() for cidr in os.getenv(
            "ALLOWED_IP_RANGES",
            "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
        ).split(",") if cidr.strip()
    ]

    # --------- Tamaño máximo de subida (para fotos del móvil) ----------
    # 15 MB por defecto
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(15 * 1024 * 1024)))

    # --------- Firma de logs (Ed25519) ----------
    # Si defines ED25519_SECRET_HEX (64 bytes hex) se usará directamente.
    # Si no, logging_utils intentará leer/crear una clave en ED25519_SECRET_PATH.
    ED25519_SECRET_HEX = os.getenv("ED25519_SECRET_HEX", None)
    ED25519_SECRET_PATH = os.getenv("ED25519_SECRET_PATH", "ed25519_secret.hex")

    # --------- Fuentes de cámaras para monitores ----------
    # Formato: "Nombre|URL,Nombre2|URL2". Por defecto usa simuladores integrados.
    CAM_URLS = [x.strip() for x in os.getenv(
        "CAM_URLS",
        "Cam 1|/camera_sim/1,Cam 2|/camera_sim/2,Cam 3|/camera_sim/3,Cam 4|/camera_sim/4"
    ).split(',') if x.strip()]

    # --------- CORS ----------
    # CSV de orígenes permitidos. Por defecto '*' para compatibilidad.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(',') if o.strip()]

    # --------- SSE / Logs ----------
    MAX_SSE_LISTENERS = int(os.getenv("MAX_SSE_LISTENERS", "100"))

cfg = Config()
