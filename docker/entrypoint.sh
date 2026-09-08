#!/bin/sh
set -e

echo "[deskline] Waiting for database..."
python - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for i in range(40):
    try:
        connection.ensure_connection()
        print("[deskline] Database ready")
        break
    except OperationalError:
        time.sleep(1.5)
else:
    raise SystemExit("[deskline] Database not reachable")
PY

echo "[deskline] Running migrations..."
python manage.py migrate --noinput

echo "[deskline] Collecting static files..."
python manage.py collectstatic --noinput

echo "[deskline] Starting: $*"
exec "$@"
