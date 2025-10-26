UPY Center IAM — Backend y Panel Web
====================================

Resumen
-------
Este proyecto implementa un backend Flask con un panel web estático para gestión de identidad (IAM) con autenticación en dos pasos (usuario+contraseña y verificación por QR). Incluye utilidades offline, migraciones de base de datos con Alembic y un modo demo para cámaras.

Arquitectura
------------
- app/__init__.py: crea la aplicación Flask, registra blueprints y ACL por IP.
- app/static/: recursos del frontend (login.html, qr.html, app.html, JS/CSS/imagenes).
- app/api/*: endpoints REST (auth, qr, usuarios, cámaras, dispositivos, etc.).
- app/models.py: modelos SQLAlchemy (usuarios, sesiones, eventos y dispositivos).
- app/db.py: engine/Base/SessionLocal.
- app/qr.py: utilidades para valores QR, hash Argon2 y render PNG temático.
- app/cli.py: CLI para crear usuarios, asignar QR y exportar PNG.
- alembic/: configuración y migraciones de BD.
- run_https.py: arranca el servidor de desarrollo con TLS local.

Flujo de autenticación
----------------------
1) login.html (usuario + contraseña) → POST /api/auth/login
   - Crea AuthSession con state=pending y ventana corta (cfg.QR_TTL_SECONDS).
2) qr.html se abre automáticamente; la cámara lee el QR (BarcodeDetector o fallback servidor)
   - POST /api/qr/scan valida el valor:
     - Si el QR pertenece al mismo usuario de la sesión → state=completed.
     - Si es de otro usuario → 403 (mismatch) y se regresa a login.
     - Si expiró → 400 (timeout) y se regresa a login.
3) app.html (panel) se habilita por 4 horas (localStorage auth_ok + auth_expires).

Roles
-----
- R-ADM (Admin): acceso total.
- R-MON (Monitoring): pestañas Cámaras + Logs.
- R-IM (IAM): pestaña Data Base (usuarios, sesiones, eventos, dispositivos) y alta rápida.
- R-AC (Access Control): panel con la última autenticación por QR.

Configuración (.env)
--------------------
- DATABASE_URL: ej. sqlite:///./iam.db (default) o postgresql+psycopg2://...
- ALLOWED_IP_RANGES: redes permitidas para /api.
- CAM_URLS: "Nombre|URL,Nombre2|URL2" (se mezclan con cámaras de la base de datos).
- MAX_CONTENT_LENGTH, claves de firma Ed25519, etc. (ver app/config.py).

Base de datos
-------------
Modelos principales (simplificado):
- Usuario: datos básicos, rol, estado, password_hash (Argon2), hash del QR, estado QR, timestamps.
- AuthSession: sesión temporal de login (pending/completed/expired).
- Evento: bitácora firmada (ed25519 + hash encadenado) de acciones relevantes.
- Dispositivos: cámaras, escáneres QR y NFC (inventario).

Alembic (migraciones)
---------------------
Alembic está preconfigurado. Variables de entorno: `DATABASE_URL`.
- Crear/migrar: `alembic revision --autogenerate -m "mensaje"` → `alembic upgrade head`.
- Historial: `alembic history -v`; Revertir: `alembic downgrade -1`.

CLI (app/cli.py)
----------------
- Crear admin inicial:
  - `python -m app.cli create-admin --uid ADMIN-1 --email admin@local --password StrongPass123!`
- Crear usuarios por rol:
  - `python -m app.cli create-user --uid MON-001 --email mon1@local --password StrongPass123! --role R-MON`
- Asignar QR (genera hash + PNG en cards/):
  - `python -m app.cli assign-qr --uid EMP-001`
- Exportar PNG de un QR específico (sin tocar BD):
  - `python -m app.cli qr-from-value --value XXXXXX --out qrs --name demo.png`

Frontend (páginas)
------------------
- login.html + login.js: credenciales y arranque de sesión temporal.
- qr.html + qr.js: escaneo con recuadro cuadrado; fallback de decodificación en servidor.
- app.html + app.js: panel por roles, temporizador en esquina, pestañas (Cámaras, Logs, Data Base, Access Control).
  - Data Base incluye secciones plegables con tablas de usuarios, sesiones, eventos y dispositivos.
  - Cámaras: grid 2x2 con paginación; soporta simuladores, MJPEG y RTSP via proxy.

Avatares
--------
Coloca `app/static/avatars/<UID>.(png|jpg|jpeg|webp)` y el panel mostrará la foto automáticamente. Si no hay, usa `/avatar.png`.

Cámaras
-------
- Simuladas: `/camera_sim/1..N`.
- Lista combinada: GET `/cameras` (CAM_URLS + BD).
- RTSP/HTTP → MJPEG: GET `/camera_mjpeg/<id>` (parámetro `?db=1` si el id es de BD).
- Escaneo simple (HTTP MJPEG): GET `/api/dev/scan?cidr=192.168.1.0/24&port=8080&path=/video&save=1`.

Modo offline
------------
Consulta README_OFFLINE.md para los pasos de venv, wheels, migraciones y ejecución sin conexión.

Ejecución
---------
- `python run_https.py` y abre `https://upy-center.local/` (o el host configurado).

Seguridad y notas
-----------------
- Este proyecto es demostrativo; para producción agregar:
  - Persistencia segura de llaves, HTTPS real, CSRF, endurecimiento de cabeceras.
  - Gateways de video más eficientes (FFmpeg/WebRTC) si hay muchas cámaras RTSP.
  - Eliminación/rotación de eventos y control de retención.
