Guía offline: dependencias, base de datos y uso del servidor
===========================================================

Esta guía resume cómo preparar un entorno completamente offline para el backend IAM, incluyendo instalación por ruedas (wheels), migraciones con Alembic y ejecución del servidor.

1) Crear y activar entorno virtual
----------------------------------
Windows (PowerShell)
- python -m venv .venv
- .\.venv\Scripts\Activate.ps1

Linux/macOS (bash)
- python3 -m venv .venv
- source .venv/bin/activate

2) Instalar dependencias (en línea una sola vez)
------------------------------------------------
- pip install -r requirements.txt

3) Descargar wheels para uso offline
------------------------------------
- PowerShell:  .\wheels\build.ps1
- Bash:        ./wheels/run.sh

Instalación completamente offline (a futuro)
- pip install --no-index --find-links=./wheels -r requirements.txt

4) Variables de entorno principales (.env)
------------------------------------------
- DATABASE_URL: cadena de conexión (por defecto sqlite:///./iam.db)
- CAM_URLS: lista de cámaras "Nombre|URL" separadas por coma (opcional)
- ALLOWED_IP_RANGES: redes permitidas para acceder a /api

5) Migraciones con Alembic
--------------------------
Alembic ya está configurado (alembic/, alembic.ini y env.py leen DATABASE_URL del entorno).

SQLite (por defecto):
- set DATABASE_URL=sqlite:///./iam.db    (Windows)
- export DATABASE_URL=sqlite:///./iam.db (Linux/macOS)
- alembic revision --autogenerate -m "init schema"
- alembic upgrade head

PostgreSQL (ejemplo):
- set DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/iam
- alembic upgrade head

Comandos útiles Alembic:
- alembic history --verbose
- alembic current -v
- alembic downgrade -1

6) Ejecutar el servidor offline
-------------------------------
- python run_https.py

El servidor sirve los estáticos desde app/static en la raíz (static_url_path="/") y la API bajo /api/*.

7) CLI y QR offline
-------------------
Crear usuarios (admin y por rol):
- python -m app.cli create-admin --uid ADMIN-001 --email admin@local --password StrongPass123!
- python -m app.cli create-user --uid MON-001 --email mon1@local --password StrongPass123! --role R-MON

Asignar QR y generar PNG (sin Internet):
- python -m app.cli assign-qr --uid EMP-001
  - Guarda el hash Argon2 en DB y un PNG del QR en cards/EMP-001_QR.png

8) Cámaras offline
------------------
Puedes usar los simuladores integrados (/camera_sim/<id>) o configurar CAM_URLS.
RTSP/RTMP se proxea como MJPEG con /camera_mjpeg/<id> para que el navegador lo vea.

9) Avatares locales
-------------------
Coloca imágenes en app/static/avatars con nombre <UID>.(png|jpg|jpeg|webp). El panel las mostrará automáticamente.
