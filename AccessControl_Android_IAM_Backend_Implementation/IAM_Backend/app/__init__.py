from flask import Flask, jsonify, send_from_directory, request, abort, redirect
from flask_cors import CORS
from .config import cfg
from .db import Base, engine
from . import models  # noqa: F401
from .net_acl import ip_allowed
from .startup import ensure_default_admin  # bootstrap admin

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/")
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = getattr(cfg, "MAX_CONTENT_LENGTH", 15 * 1024 * 1024)
    # Configurar CORS con orígenes permitidos (configurable por env)
    try:
        origins = cfg.CORS_ORIGINS or ["*"]
        if origins == ["*"]:
            CORS(app)
        else:
            CORS(app, resources={r"/api/*": {"origins": origins}})
    except Exception:
        CORS(app)

    # Tablas y bootstrap admin
    Base.metadata.create_all(bind=engine)
    ensure_default_admin()

    # ACL simple por IP (static libre; API protegida)
    @app.before_request
    def _enforce_acl():
        remote = request.headers.get("X-Forwarded-For", request.remote_addr)
        path = request.path or "/"
        safe_paths = {"/health", "/favicon.ico", "/", "/login.html", "/app.html", "/qr.html"}
        is_static = path.startswith("/static/") or any(path.endswith(ext) for ext in (
            ".html", ".css", ".js", ".png", ".ico", ".svg", ".jpg", ".jpeg", ".webp"
        ))
        if path in safe_paths or is_static:
            return
        if not ip_allowed(remote, cfg.ALLOWED_IP_RANGES):
            if path.startswith("/api/"):
                abort(403, description="IP not allowed")
            return redirect("/login.html", code=302)

    # Blueprints API
    from .api.auth_routes import bp as auth_bp
    from .api.qr_routes import bp as qr_bp
    from .api.ingest_routes import bp as ingest_bp
    from .api.admin_routes import bp as admin_bp
    from .api.camera_sim import bp as cam_bp
    from .api.devices_routes import bp as dev_bp
    from .api.nfc_sim import bp as nfc_sim_bp  # NFC simulator
    from .api.nfc_routes import bp as nfc_bp  # NFC Android app integration
    from .api.user_routes import bp as user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(qr_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cam_bp)
    app.register_blueprint(nfc_sim_bp)  # NFC simulator
    app.register_blueprint(nfc_bp)      # NFC Android app
    app.register_blueprint(dev_bp)
    app.register_blueprint(user_bp)
    # Extra blueprints: messages + access log
    from .api.messages_routes import bp as messages_bp
    from .api.access_routes import bp as access_bp
    app.register_blueprint(messages_bp)
    app.register_blueprint(access_bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def root():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(detail="not found"), 404
        return redirect("/login.html", code=302)

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify(detail=getattr(e, "description", "forbidden")), 403
        return redirect("/login.html", code=302)

    return app
