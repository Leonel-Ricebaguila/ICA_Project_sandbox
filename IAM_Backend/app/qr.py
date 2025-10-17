# app/qr.py — Utilidades de QR (valor, hash y render temático UPY)
# ✔ Genera valor QR (Base32)
# ✔ Hashea/verifica con Argon2
# ✔ Renderiza SOLO el QR en un lienzo cuadrado con tema UPY Center (sin datos personales)

import os
import base64
import hashlib
from typing import Optional

from argon2 import PasswordHasher
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode

from .config import cfg

ph = PasswordHasher()


# ---------------------------
# Valor del QR (estático por tarjeta)
# ---------------------------
def gen_qr_value_b32(n_bytes: int = None) -> str:
    """Genera un valor de QR aleatorio en Base32 (sin '=') para imprimir en tarjetas."""
    n = n_bytes or cfg.QR_BYTES
    return base64.b32encode(os.urandom(n)).decode().rstrip("=")


def hash_qr_value(qr_value: str) -> str:
    """Hash Argon2 del valor QR (lo que se guarda en BD)."""
    return ph.hash(qr_value)


def verify_qr_value(qr_value: str, qr_hash: str) -> bool:
    """Verifica un valor QR contra su hash Argon2 almacenado."""
    try:
        return ph.verify(qr_hash, qr_value)
    except Exception:
        return False


def qr_value_fingerprint(qr_value: str) -> str:
    """Huella (no secreta) solo para control visual o trazas."""
    return hashlib.sha256(qr_value.encode()).hexdigest()


# ---------------------------
# Render del QR (temático UPY)
# ---------------------------
def _try_load_font(size: int):
    """Intenta cargar una fuente del sistema; si falla, usa la por defecto."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill=None, outline=None, width: int = 1):
    """Dibuja un rectángulo redondeado compatible en PIL."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def make_upy_qr_image(
    qr_value: str,
    size: int = 600,
    logo_path: Optional[str] = None,
    accent: str = "#0b2a3c",   # UPY primary
    accent2: str = "#2f7ea1",  # UPY accent
    bg: str = "#f5f7fb",
) -> Image.Image:
    """
    Crea una imagen cuadrada con SOLO el código QR (tema UPY):
    - Lienzo con fondo claro y marco redondeado UPY.
    - QR centrado en color UPY.
    - (Opcional) watermark/logo pequeño al centro (<= 18% del QR) para mantener scaneabilidad.
    - Sin texto de identificación.

    size: tamaño final (px) del lienzo cuadrado (ej. 600, 800, 1024).
    """
    # Lienzo final
    W = H = size
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    # Marco temático
    pad = int(size * 0.055)           # padding externo
    radius = int(size * 0.08)         # radio del marco
    _rounded_rect(draw, (pad, pad, W - pad, H - pad), radius=radius, fill="white", outline=accent, width=3)

    # Área interna para el QR
    inner_pad = int(size * 0.12)
    qr_box = (inner_pad, inner_pad, W - inner_pad, H - inner_pad)
    qr_side = qr_box[2] - qr_box[0]

    # Generar QR monocromo con color UPY
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% tolerancia (permite logo pequeño)
        box_size=10,
        border=0,
    )
    qr.add_data(qr_value)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=accent, back_color="white").convert("RGBA")

    # Ajustar tamaño del QR a la caja
    qr_img = qr_img.resize((qr_side, qr_side), Image.LANCZOS)

    # Pegar QR en lienzo
    canvas.paste(qr_img, (qr_box[0], qr_box[1]), qr_img)

    # Borde sutil alrededor del QR
    border_pad = int(size * 0.01)
    _rounded_rect(
        draw,
        (qr_box[0] - border_pad, qr_box[1] - border_pad, qr_box[2] + border_pad, qr_box[3] + border_pad),
        radius=int(radius * 0.6),
        outline=accent2,
        width=2,
    )

    # (Opcional) Watermark/logo pequeño en el centro del QR
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Tamaño del logo: ~16% del lado del QR para no afectar la lectura
            lw = int(qr_side * 0.16)
            logo = logo.resize((lw, lw), Image.LANCZOS)

            # Fondo blanco muy ligero detrás del logo para contraste
            pad2 = int(lw * 0.14)
            bg_logo = Image.new("RGBA", (lw + pad2 * 2, lw + pad2 * 2), (255, 255, 255, 220))
            bx = qr_box[0] + (qr_side - lw) // 2 - pad2
            by = qr_box[1] + (qr_side - lw) // 2 - pad2
            canvas.paste(bg_logo, (bx, by), bg_logo)

            # Pegar logo centrado
            lx = qr_box[0] + (qr_side - lw) // 2
            ly = qr_box[1] + (qr_side - lw) // 2
            canvas.paste(logo, (lx, ly), logo)
        except Exception:
            pass

    # Sombra suave exterior del marco (opcional, estética)
    try:
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        _rounded_rect(sd, (pad, pad, W - pad, H - pad), radius=radius, fill=(0, 0, 0, 40))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")
    except Exception:
        pass

    return canvas


def save_upy_qr_png(path: str, qr_value: str, size: int = 600, logo_path: Optional[str] = None) -> None:
    """Crea y guarda un PNG del QR temático UPY (solo código QR)."""
    img = make_upy_qr_image(qr_value=qr_value, size=size, logo_path=logo_path)
    img.save(path, format="PNG")
