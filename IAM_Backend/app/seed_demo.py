"""
Datos demo inspirados en ICA_Project/config_datos.py para poblar entorno local.

Activación por CLI:
  python -m app.cli seed-demo

Opcionalmente puedes pasar usuarios con contraseña:
  python -m app.cli seed-demo --users "EMP-0001|user1@mail|Pass1!|R-ADM|Nombre|Apellido,EMP-0002|user2@mail|Pass2!|R-EMP|N|A"

O desde un CSV (uid,email,password,role,nombre,apellido):
  python -m app.cli seed-demo --users-file users.csv [--update-existing]
"""
from .db import SessionLocal
from .models import Usuario, CameraDevice, QRScannerDevice, NFCDevice, Mensaje
from .auth import hash_password
from .logging_utils import sign_event_and_persist


USUARIOS = [
    # Formatos aceptados por compatibilidad:
    #  - (uid, email, rol, nombre, apellido)
    #  - (uid, email, rol, nombre, apellido, password)
    # Un usuario por rol existente, incluyendo guardia y visitantes
    ("MON-001", "monitor@local",      "R-MON", "Monitor", "Uno",     "DemoPass123!"),
    ("IM-001",  "im@local",          "R-IM",  "IM",     "Ops",     "DemoPass123!"),
    ("AC-001",  "access@local",       "R-AC",  "Access",  "Ctrl",    "DemoPass123!"),
    ("EMP-001", "empleado@local",     "R-EMP", "Empleado","Demo",    "DemoPass123!"),
    ("GRD-001", "guardia@local",      "R-GRD", "Guardia", "TurnoA",  "DemoPass123!"),
    ("AUD-001", "auditor@local",      "R-AUD", "Auditor", "Demo",    "DemoPass123!"),
]

CAMERAS = [
    ("Cam_Puerta_1", "127.0.0.1", "/camera_sim/1", "DataCenter - Puerta 1"),
    ("Cam_Pasillo_2", "127.0.0.2", "/camera_sim/2", "Oficina - Pasillo"),
]

QR_SCANNERS = [
    ("Reader_Puerta_1", "127.0.0.31", None, "DataCenter - Puerta 1"),
]

NFC_DEVICES = [
    ("NFC_Puerta_1", "127.0.0.41", 8080, "DataCenter - Puerta 1"),
]


def _iter_users(base_users, override_users=None):
    """Itera usuarios combinando defaults con overrides.

    override_users: lista de dicts o tuplas en formato
      (uid, email, role, nombre, apellido, password)
    """
    if override_users:
        for u in override_users:
            if isinstance(u, dict):
                yield (
                    u.get("uid"), u.get("email"), u.get("role", u.get("rol", "R-EMP")),
                    u.get("nombre", ""), u.get("apellido", ""), u.get("password", "Passw0rd!")
                )
            else:
                # tupla/lista
                if len(u) == 5:
                    uid, email, rol, nombre, apellido = u
                    password = "Passw0rd!"
                else:
                    uid, email, rol, nombre, apellido, password = u
                yield (uid, email, rol, nombre, apellido, password)
    else:
        for u in base_users:
            if len(u) == 5:
                uid, email, rol, nombre, apellido = u
                password = "Passw0rd!"
            else:
                uid, email, rol, nombre, apellido, password = u
            yield (uid, email, rol, nombre, apellido, password)


def seed_demo(users_override=None, update_existing=False):
    db = SessionLocal()
    try:
        # Usuarios
        for uid, email, rol, nombre, apellido, password in _iter_users(USUARIOS, users_override):
            ex_uid = db.query(Usuario).filter(Usuario.uid == uid).first()
            ex_email = db.query(Usuario).filter(Usuario.email == email).first()

            if ex_uid:
                if update_existing:
                    ex_uid.email = email or ex_uid.email
                    ex_uid.rol = rol or ex_uid.rol
                    ex_uid.nombre = nombre or ex_uid.nombre
                    ex_uid.apellido = apellido or ex_uid.apellido
                    if password:
                        ex_uid.password_hash = hash_password(password)
                    try:
                        sign_event_and_persist(db, "user_updated", actor_uid=ex_uid.uid, source="seed_demo", context={"rol": ex_uid.rol})
                    except Exception:
                        pass
                # si no se solicita update, lo dejamos tal cual
                continue

            if ex_email and not ex_uid:
                # El email ya existe con otro UID (p.ej. admin@local creado en startup)
                if update_existing:
                    ex_email.rol = rol or ex_email.rol
                    ex_email.nombre = nombre or ex_email.nombre
                    ex_email.apellido = apellido or ex_email.apellido
                    if password:
                        ex_email.password_hash = hash_password(password)
                # No intentamos crear un nuevo registro para no violar UNIQUE(email)
                continue

            # No existe ni UID ni email -> crear
            u = Usuario(
                uid=uid,
                email=email,
                rol=rol,
                nombre=nombre,
                apellido=apellido,
                estado="active",
                password_hash=hash_password(password or "Passw0rd!"),
            )
            db.add(u)
            try:
                sign_event_and_persist(db, "user_created", actor_uid=u.uid, source="seed_demo", context={"rol": u.rol})
            except Exception:
                pass
        db.commit()

        # Cámaras
        for name, ip, url, location in CAMERAS:
            exists = db.query(CameraDevice).filter(CameraDevice.name == name).first()
            if not exists:
                db.add(CameraDevice(name=name, ip=ip, url=url, location=location))
        db.commit()

        # QR Scanners
        for name, ip, url, location in QR_SCANNERS:
            exists = db.query(QRScannerDevice).filter(QRScannerDevice.name == name).first()
            if not exists:
                db.add(QRScannerDevice(name=name, ip=ip, url=url, location=location))
        db.commit()

        # NFC Devices
        for name, ip, port, location in NFC_DEVICES:
            exists = db.query(NFCDevice).filter(NFCDevice.name == name).first()
            if not exists:
                db.add(NFCDevice(name=name, ip=ip, port=port, location=location))
        db.commit()

        print("[seed-demo] Datos cargados.")
    finally:
        db.close()
