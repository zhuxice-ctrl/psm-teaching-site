#!/bin/bash
# Minimal smoke test for PSM Teaching Site
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-.venv/bin/python3}"
if [ ! -x "$PY" ]; then PY=python3; fi

echo "=== PSM Teaching Site Smoke Test ==="
echo ""

echo "1. py_compile check..."
"$PY" - <<'PY'
import py_compile, glob, sys
errors = 0
for f in glob.glob('app/**/*.py', recursive=True):
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        print(f'COMPILE ERROR: {e}')
        errors += 1
for f in ['run.py', 'config.py']:
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        print(f'COMPILE ERROR: {e}')
        errors += 1
if errors:
    sys.exit(1)
print('py_compile: ALL PASS')
PY

echo ""
echo "2. Unit tests..."
"$PY" tests/test_app.py

echo ""
echo "3. Init DB + start smoke..."
rm -f instance/psm.db
export PSM_ADMIN_USER=admin
export PSM_ADMIN_PASS=testpass123
"$PY" - <<'PY'
import sys
sys.path.insert(0, '.')
from app import create_app, get_db, init_db
from run import ensure_admin
app = create_app()
with app.app_context():
    db = get_db()
    init_db(db)
    db.commit()
    ensure_admin()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = [t['name'] for t in tables]
    print(f'DB tables: {names}')
    assert 'teacher' in names and 'student' in names and 'quota_ledger' in names
    admin = db.execute('SELECT * FROM teacher WHERE username=?', ('admin',)).fetchone()
    print(f'Admin exists: {admin is not None}')
    assert admin is not None
print('DB init: PASS')
PY

echo ""
echo "4. Flask app smoke (quick import test)..."
"$PY" - <<'PY'
import sys
sys.path.insert(0, '.')
from app import create_app
app = create_app()
client = app.test_client()
r = client.get('/health')
assert r.status_code == 200, f'health failed: {r.status_code}'
r = client.get('/')
assert r.status_code == 200, f'index failed: {r.status_code}'
print('Flask smoke: PASS')
PY

echo ""
echo "=== SMOKE TEST COMPLETE ==="
