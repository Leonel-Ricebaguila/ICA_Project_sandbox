# app/cli.py — CLI de utilidades
# - create-admin  → alta del usuario admin inicial
# - create-user   → alta de usuarios por rol (R-ADM/R-MON/R-IM/R-AC/R-EMP/R-GRD/R-AUD)
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
from .user_qr import assign_qr_to_user, resolve_outdir
from .seed_demo import seed_demo
from .startup import DEFAULT_ADMIN
from .models import Usuario


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
        # Auto-assign QR and PNG
        try:
            assign_qr_to_user(uid)
        except Exception as e:
            print("[cli] auto-assign QR failed:", e)
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
        # Auto-assign QR and PNG
        try:
            assign_qr_to_user(uid)
        except Exception as e:
            print("[cli] auto-assign QR failed:", e)
    finally:
        db.close()

def assign_qr(uid, outdir="cards", size=600):
    """Emite/rota el QR y guarda PNG (tema UPY)."""
    try:
        qr_val, png_path = assign_qr_to_user(uid, outdir=outdir, size=size)
        print("QR assigned (PRINT THIS VALUE):\n", qr_val)
        print("Saved PNG:", png_path)
    except Exception as e:
        print("assign_qr failed:", e)


def assign_qr_bulk(missing_only=True, outdir="cards", size=600):
    """Asigna/rota QR para muchos usuarios.

    - missing_only=True: solo usuarios sin `qr_value_hash`.
    - missing_only=False: rota QR para todos los usuarios.
    """
    # Capturamos sólo los UID para evitar problemas de instancia detach/expire
    db = SessionLocal()
    try:
        q = db.query(Usuario.uid)
        if missing_only:
            q = q.filter((Usuario.qr_value_hash == None))  # noqa: E711
        uids = [row[0] for row in q.all()]
    finally:
        db.close()

    if not uids:
        print("[assign-qr-bulk] No users matched condition.")
        return
    ok = 0; fail = 0
    for uid in uids:
        try:
            assign_qr_to_user(uid, outdir=outdir, size=int(size))
            ok += 1
        except Exception as e:
            print(f"[assign-qr-bulk] Failed {uid}: {e}")
            fail += 1
    print(f"[assign-qr-bulk] Done. OK={ok} FAIL={fail}")


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
    s1b.add_argument("--role", required=True, choices=["R-ADM","R-MON","R-IM","R-AC","R-EMP","R-GRD","R-AUD"])
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

    s4 = sub.add_parser("seed-demo")
    s4.add_argument(
        "--users",
        default=None,
        help=(
            "Lista separada por coma de usuarios: "
            "uid|email|password|role|nombre|apellido,uid2|..."
        ),
    )
    s4.add_argument(
        "--users-file",
        default=None,
        help=(
            "Ruta a CSV con columnas: uid,email,password,role,nombre,apellido"
        ),
    )
    s4.add_argument(
        "--update-existing",
        action="store_true",
        help="Si está presente, actualiza email/rol/nombre/apellido y password de usuarios existentes",
    )

    s5 = sub.add_parser("assign-qr-bulk")
    s5.add_argument("--all", action="store_true", help="Rotar QR para TODOS los usuarios")
    s5.add_argument("--out", default="cards", help="Carpeta para guardar PNGs de QR")
    s5.add_argument("--size", default=600, help="Tamaño (px) del PNG cuadrado")

    s6 = sub.add_parser("wipe-db")
    s6.add_argument("--keep-uid", default=DEFAULT_ADMIN.get("uid", "ADMIN-1"), help="UID a conservar (admin)")
    s6.add_argument("--yes", action="store_true", help="Confirmación explícita: borra todo excepto el admin indicado")

    args = p.parse_args()

    if args.cmd == "create-admin":
        create_admin(args.uid, args.email, args.password)

    elif args.cmd == "create-user":
        create_user(args.uid, args.email, args.password, args.role, args.nombre, args.apellido)

    elif args.cmd == "assign-qr":
        assign_qr(args.uid, outdir=args.out, size=args.size)

    elif args.cmd == "qr-from-value":
        qr_from_value(args.value, outdir=args.out, filename=args.name, size=args.size)

    elif args.cmd == "seed-demo":
        overrides = None
        # Parse --users inline list
        if args.users:
            overrides = []
            items = [x.strip() for x in str(args.users).split(",") if x.strip()]
            for it in items:
                parts = [p.strip() for p in it.split("|")]
                if len(parts) < 6:
                    # pad missing name/lastname if needed; require at least uid,email,password,role
                    parts = (parts + [""] * 6)[:6]
                uid, email, password, role, nombre, apellido = parts
                overrides.append((uid, email, role, nombre, apellido, password))
        # Parse --users-file CSV if provided
        if args.users_file and not overrides:
            import csv
            overrides = []
            with open(args.users_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    overrides.append({
                        "uid": row.get("uid"),
                        "email": row.get("email"),
                        "password": row.get("password"),
                        "role": row.get("role") or row.get("rol") or "R-EMP",
                        "nombre": row.get("nombre", ""),
                        "apellido": row.get("apellido", ""),
                    })
        seed_demo(users_override=overrides, update_existing=bool(args.update_existing))

    elif args.cmd == "assign-qr-bulk":
        assign_qr_bulk(missing_only=(not args.all), outdir=args.out, size=args.size)

    elif args.cmd == "wipe-db":
        if not args.yes:
            print("[wipe-db] Esta operación elimina TODAS las tablas excepto el usuario admin. Repite con --yes para confirmar.")
        else:
            from .models import AuthSession, Evento, Mensaje, CameraDevice, QRScannerDevice, NFCDevice
            import os
            db = SessionLocal()
            try:
                # Capturar UIDs a eliminar para limpiar sus cards luego
                del_uids = [row[0] for row in db.query(Usuario.uid).filter(Usuario.uid != args.keep_uid).all()]

                # Eliminar dependientes primero
                n_sessions = db.query(AuthSession).delete(synchronize_session=False)
                n_events = db.query(Evento).delete(synchronize_session=False)
                n_msgs = db.query(Mensaje).delete(synchronize_session=False)
                n_cam = db.query(CameraDevice).delete(synchronize_session=False)
                n_qr = db.query(QRScannerDevice).delete(synchronize_session=False)
                n_nfc = db.query(NFCDevice).delete(synchronize_session=False)
                # Usuarios: conservar admin solicitado
                n_users = db.query(Usuario).filter(Usuario.uid != args.keep_uid).delete(synchronize_session=False)
                db.commit()

                # Borrar PNGs de tarjetas de usuarios eliminados y huérfanos
                cards_dir = resolve_outdir("cards")
                removed_png = 0
                removed_orphan = 0
                # 1) Remove for known deleted UIDs
                for uid in del_uids:
                    try:
                        path = os.path.join(cards_dir, f"{uid}_QR.png")
                        if os.path.exists(path):
                            os.remove(path)
                            removed_png += 1
                    except Exception:
                        pass
                # 2) Remove any orphan PNG in cards/ that doesn't have a user in DB
                try:
                    remaining = {row[0] for row in db.query(Usuario.uid).all()}
                    for name in os.listdir(cards_dir):
                        if not name.endswith("_QR.png"):
                            continue
                        uid_part = name[:-7]  # strip '_QR.png'
                        if uid_part not in remaining:
                            fpath = os.path.join(cards_dir, name)
                            if os.path.exists(fpath):
                                os.remove(fpath)
                                removed_orphan += 1
                except Exception:
                    pass

                try:
                    sign_event_and_persist(db, "db_wipe", actor_uid=args.keep_uid, source="cli", context={
                        "deleted": {
                            "auth_sessions": n_sessions,
                            "eventos": n_events,
                            "mensajes": n_msgs,
                            "devices": {"cameras": n_cam, "qr_scanners": n_qr, "nfc": n_nfc},
                            "usuarios_except_admin": n_users,
                            "cards_png_removed": removed_png,
                            "cards_png_orphan_removed": removed_orphan,
                        }
                    })
                except Exception:
                    pass
                print(f"[wipe-db] OK. Eliminados usuarios(excepto {args.keep_uid})={n_users}, sesiones={n_sessions}, eventos={n_events}, mensajes={n_msgs}, cam={n_cam}, qr={n_qr}, nfc={n_nfc}, cards_png_removed={removed_png}, cards_png_orphan_removed={removed_orphan}")
            finally:
                db.close()
