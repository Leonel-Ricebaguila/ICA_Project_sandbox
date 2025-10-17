# app/cli.py — CLI de utilidades
# - create-admin  → alta del usuario admin inicial
# - create-user   → alta de usuarios por rol (R-ADM/R-MON/R-IM/R-AC/R-EMP)
# - assign-qr     → emite/rota el valor de QR y exporta PNG del código (tema UPY)
# - qr-from-value → genera PNG del QR a partir de un valor dado (sin tocar BD)

import argparse
import os

from .db import SessionLocal, engine, Base
import app.models  # noqa: F401  -> registra modelos
Base.metadata.create_all(bind=engine)

from .models import Usuario
from .auth import hash_password
from .qr import gen_qr_value_b32, hash_qr_value, save_upy_qr_png
from .logging_utils import sign_event_and_persist


# Intentar encontrar un logo local para watermark opcional
STATIC_LOGO_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "static", "favicon-512.png"),
    os.path.join(os.path.dirname(__file__), "static", "apple-touch-icon.png"),
]
def resolve_logo():
    """Intenta localizar un logo estático para watermark opcional en el QR."""
    for p in STATIC_LOGO_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def create_admin(uid, email, password):
    """Crea el usuario administrador con contraseña inicial.

    Se registra un evento firmado en la bitácora para auditoría.
    """
    db = SessionLocal()
    try:
        u = Usuario(
            uid=uid,
            nombre="Admin",
            apellido="",
            email=email,
            rol="R-ADM",
            estado="active",
            password_hash=hash_password(password),
            mfa_enabled=False,
        )
        db.add(u)
        db.commit()
        sign_event_and_persist(db, "user_created", actor_uid=uid, source="cli", context={})
        print("admin created")
    finally:
        db.close()


def create_user(uid, email, password, role, nombre="", apellido=""):
    """Crea un usuario genérico con rol especificado."""
    db = SessionLocal()
    try:
        u = Usuario(
            uid=uid,
            nombre=nombre or "",
            apellido=apellido or "",
            email=email,
            rol=role,
            estado="active",
            password_hash=hash_password(password),
            mfa_enabled=False,
        )
        db.add(u)
        db.commit()
        sign_event_and_persist(db, "user_created", actor_uid=uid, source="cli", context={"rol": role})
        print(f"user created: {uid} ({role})")
    finally:
        db.close()

def assign_qr(uid, outdir="cards", size=600):
    """
    Emite/rota el valor QR de un usuario y genera la imagen PNG por defecto.
    - Genera valor nuevo (Base32) y lo guarda hasheado en BD.
    - Siempre exporta un PNG temático UPY del código QR a la carpeta 'cards/'
      en la raíz del proyecto, salvo que se indique --out con otra ruta.
    """
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.uid == uid).first()
        if not user:
            print("user not found")
            return

        qr_val = gen_qr_value_b32()
        user.qr_value_hash = hash_qr_value(qr_val)
        db.commit()

        sign_event_and_persist(
            db,
            "qr_assigned_cli",
            actor_uid=uid,
            source="cli",
            context={"qr_card_preview": qr_val[:6] + "..."},
        )

        print("QR assigned (PRINT THIS VALUE):\n", qr_val)

        # Resolver carpeta de salida: por defecto 'cards/' en la raíz del repo
        if not os.path.isabs(outdir):
            proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            outdir = os.path.join(proj_root, outdir)
        os.makedirs(outdir, exist_ok=True)
        logo = resolve_logo()
        png_path = os.path.join(outdir, f"{uid}_QR.png")
        save_upy_qr_png(png_path, qr_value=qr_val, size=int(size), logo_path=logo)
        print("Saved PNG:", png_path)

    finally:
        db.close()


def qr_from_value(qr_value, outdir=".", filename="QR_custom.png", size=600):
    """
    Exporta un PNG de SOLO el QR (tema UPY) a partir de un valor dado (no toca BD).
    Útil si te pasaron el valor por otra vía.
    """
    os.makedirs(outdir, exist_ok=True)
    logo = resolve_logo()
    path = os.path.join(outdir, filename)
    save_upy_qr_png(path, qr_value=qr_value, size=int(size), logo_path=logo)
    print("Saved PNG:", path)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("create-admin")
    s1.add_argument("--uid", required=True)
    s1.add_argument("--email", required=True)
    s1.add_argument("--password", required=True)

    s1b = sub.add_parser("create-user")
    s1b.add_argument("--uid", required=True)
    s1b.add_argument("--email", required=True)
    s1b.add_argument("--password", required=True)
    s1b.add_argument("--role", required=True, choices=["R-ADM","R-MON","R-IM","R-AC","R-EMP"])
    s1b.add_argument("--nombre", default="")
    s1b.add_argument("--apellido", default="")

    s2 = sub.add_parser("assign-qr")
    s2.add_argument("--uid", required=True)
    s2.add_argument("--out", default="cards", help="Carpeta para guardar el PNG del QR (por defecto: cards/)")
    s2.add_argument("--size", default=600, help="Tamaño (px) del PNG cuadrado (ej. 600, 800, 1024)")

    s3 = sub.add_parser("qr-from-value")
    s3.add_argument("--value", required=True, help="Valor de QR en texto (Base32)")
    s3.add_argument("--out", default=".", help="Carpeta de salida")
    s3.add_argument("--name", default="QR_custom.png", help="Nombre de archivo (p. ej., EMP-001.png)")
    s3.add_argument("--size", default=600, help="Tamaño (px) del PNG cuadrado")

    args = p.parse_args()

    if args.cmd == "create-admin":
        create_admin(args.uid, args.email, args.password)

    elif args.cmd == "create-user":
        create_user(args.uid, args.email, args.password, args.role, args.nombre, args.apellido)

    elif args.cmd == "assign-qr":
        assign_qr(args.uid, outdir=args.out, size=args.size)

    elif args.cmd == "qr-from-value":
        qr_from_value(args.value, outdir=args.out, filename=args.name, size=args.size)
