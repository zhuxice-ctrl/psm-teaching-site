import os
import sqlite3
from flask import Flask, g
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from flask_login import LoginManager

login_manager = LoginManager()


def _normalise_prefix(prefix):
    prefix = (prefix or "").strip()
    if not prefix or prefix == "/":
        return ""
    return "/" + prefix.strip("/")


class PrefixMountMiddleware:
    """Serve the app under a mount prefix for both direct and proxied requests."""

    def __init__(self, app, prefix="/psm"):
        self.app = app
        self.prefix = _normalise_prefix(prefix)

    def _trusted_header_prefix(self, environ):
        for key in ("HTTP_X_FORWARDED_PREFIX", "HTTP_X_SCRIPT_NAME"):
            header_prefix = _normalise_prefix(environ.get(key, "").split(",", 1)[0])
            if header_prefix == self.prefix:
                return header_prefix
        return ""

    def __call__(self, environ, start_response):
        if not self.prefix:
            return self.app(environ, start_response)
        path = environ.get("PATH_INFO", "")
        if path == self.prefix or path.startswith(self.prefix + "/"):
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
        elif _normalise_prefix(environ.get("SCRIPT_NAME")) == self.prefix or self._trusted_header_prefix(environ):
            environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


def get_db():
    if "db" not in g:
        from flask import current_app
        db_path = current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        if db_path != ":memory:":
            g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        db.executescript(f.read())


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)
    app.secret_key = app.config["SECRET_KEY"]

    # Reverse-proxy support plus direct local smoke on /psm/* without nginx.
    # ProxyFix handles standard X-Forwarded-Prefix; PrefixMountMiddleware also
    # accepts X-Script-Name and strips a direct /psm path exactly once.
    prefix = app.config.get("APPLICATION_ROOT", "/psm")
    app.wsgi_app = ProxyFix(
        PrefixMountMiddleware(app.wsgi_app, prefix=prefix),
        x_for=1,
        x_proto=1,
        x_prefix=1,
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    if db_path and db_path != ":memory:":
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login_chooser"

    app.teardown_appcontext(close_db)

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.teacher import bp as teacher_bp
    from app.blueprints.student import bp as student_bp
    from app.blueprints.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Schema creation is idempotent and doubles as the lightweight migration
    # required by old deployments. Workers start only after durable storage exists.
    with app.app_context():
        db = get_db()
        init_db(db)
        db.commit()
    if app.config.get("IMAGE_WORKERS_ENABLED", True):
        from app.blueprints.api import start_image_workers
        start_image_workers(app)

    @app.route("/")
    def index():
        from flask import render_template
        return render_template("index.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
