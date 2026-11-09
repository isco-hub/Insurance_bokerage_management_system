#!/bin/sh
set -e

if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  echo "Waiting for database..."
  python - <<'PY'
import os
import time

import dj_database_url
import psycopg

raw = os.environ.get('DATABASE_URL', 'postgres://ibms:ibms@db:5432/ibms')
config = dj_database_url.parse(raw)
for attempt in range(60):
    try:
        conn = psycopg.connect(
            host=config['HOST'],
            port=config['PORT'] or 5432,
            dbname=config['NAME'],
            user=config['USER'],
            password=config['PASSWORD'],
        )
        conn.close()
        print('Database is ready')
        break
    except Exception as exc:  # noqa: BLE001
        print(f'Database not ready ({attempt + 1}/60): {exc}')
        time.sleep(1)
else:
    raise SystemExit('Database did not become available in time')
PY
fi

python manage.py migrate --noinput

if [ "${SEED_ON_START:-0}" = "1" ]; then
  python manage.py seed
fi

if [ "${COLLECT_STATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput >/dev/null 2>&1 || true
fi

exec "$@"
