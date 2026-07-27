import os, sys

# Load .env before anything else
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from app import create_app, get_db, init_db

app = create_app()


def ensure_admin():
    """Ensure admin teacher exists in DB."""
    db = get_db()
    with app.app_context():
        from app import get_db as gdb
        d = gdb()
        from config import Config
        import hashlib
        pw_hash = hashlib.sha256(Config.PSM_ADMIN_PASS.encode()).hexdigest()
        d.execute(
            "INSERT OR IGNORE INTO teacher(username, password_hash, display_name) VALUES(?,?,?)",
            (Config.PSM_ADMIN_USER, pw_hash, "管理员"),
        )
        d.commit()


if __name__ == "__main__":
    with app.app_context():
        db = get_db()
        init_db(db)
        db.commit()
        ensure_admin()
    print("Starting PSM Teaching Site on 127.0.0.1:8800")
    # Production service must not auto-reload while in-memory image jobs run.
    # A reload discards job IDs and leaves classroom browsers polling forever.
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host="127.0.0.1", port=8800, debug=debug, use_reloader=debug)
