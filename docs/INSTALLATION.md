# Installation and Deployment Guide

This guide covers the containerised stack (recommended), local development and
production hardening for the Insurance Brokerage Management System.

## 1. Prerequisites

| Tool | Minimum | Notes |
| --- | --- | --- |
| Docker Engine | 24 | Docker Desktop is fine |
| Docker Compose | v2 | `docker compose` plugin |
| Python | 3.12 | Only needed for non-Docker backend development |
| Node.js | 22 | Only needed for non-Docker frontend development |
| PostgreSQL | 16 | Only needed for non-Docker database work |
| Redis | 7 | Optional locally; recommended for shared throttle counters |
| Chrome/Chromium | current | Only needed for the UI smoke test |

Ports used by default: web `8080`, API `4000`, PostgreSQL `5434`. Override them in
`.env` before starting the stack.

## 2. Docker quick start

```bash
cp .env.example .env
# edit .env: set a strong DJANGO_SECRET_KEY and non-default passwords
docker compose up --build -d
docker compose ps
```

The stack includes PostgreSQL, Redis (shared throttle cache), the Django API and the
nginx web container. The API entrypoint will:

1. wait for PostgreSQL to accept connections;
2. apply Django migrations (`manage.py migrate`);
3. run the idempotent seed command when `SEED_ON_START=1`;
4. collect static files when `COLLECT_STATIC=1`;
5. start Gunicorn.

Open http://localhost:8080 to see the landing page, choose **Sign in**, and use a
demo account (password `Password123!` unless `SEED_PASSWORD` was changed):

| Role | Email |
| --- | --- |
| System Administrator | admin@ibms.local |
| Managing Director | md@ibms.local |
| Operations Manager | ops@ibms.local |
| Branch Manager | branch@ibms.local |
| Broker / Relationship Manager | broker@ibms.local |
| Underwriting Officer | underwriting@ibms.local |
| Claims Officer | claims@ibms.local |
| Finance Officer | finance@ibms.local |
| Customer Service Officer | service@ibms.local |
| Auditor | auditor@ibms.local |

Useful commands:

```bash
docker compose logs -f api          # follow API logs
docker compose exec api python manage.py seed          # reseed demo data
docker compose exec api python manage.py createsuperuser
docker compose exec api python manage.py shell         # ORM shell
docker compose exec api python manage.py migrate       # apply new migrations
docker compose restart api          # restart after code changes
docker compose down                 # stop containers, keep volumes
docker compose logs -f cache        # Redis cache logs
docker compose down -v              # stop and DELETE database/media volumes
```

> `docker compose down -v` destroys the database volume. Use it only when you intend
> to start from a clean database.

## 3. Local development without Docker

### 3.1 Database

Create a PostgreSQL database and user:

```sql
CREATE USER ibms WITH PASSWORD 'ibms';
CREATE DATABASE ibms OWNER ibms;
```

### 3.2 Backend

Django loads `backend/.env` when running outside Docker. Create it with at least:

```env
DJANGO_SECRET_KEY=local-development-key
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://ibms:ibms@localhost:5432/ibms
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8080
SEED_ON_START=0
```

Then:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # optional demo data
python manage.py runserver 0.0.0.0:4000
```

The API is available at http://localhost:4000/api/ and the health check at
http://localhost:4000/api/health/.

### 3.3 Frontend

```bash
cd frontend
npm ci
npm run dev
```

Vite serves http://localhost:5173 and proxies `/api` and `/media` to
http://localhost:4000 by default. To build against a different API origin:

```bash
VITE_API_URL=http://localhost:4000/api npm run build
```

### 3.4 Smoke tests

With the seed data loaded and the stack running:

```bash
docker compose exec -T api python manage.py test
./scripts/smoke_api.sh
node scripts/smoke_ui.mjs
```

The UI test needs `playwright-core` (installed by `npm ci` in `frontend`) and a
local Chrome/Chromium. Set `CHROME_PATH=/path/to/chrome` if detection fails. See
[`TESTING.md`](TESTING.md).

## 4. Configuration reference

Environment variables are read from `.env` by Docker Compose and from
`backend/.env` by Django when running locally.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev key | Cryptographic signing; **must** be changed in production |
| `DJANGO_DEBUG` | `false` (compose), `true` (settings default) | Debug mode; keep `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,api` | Comma-separated host allow-list |
| `TIME_ZONE` | `Africa/Kampala` | Business timezone |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `ibms` | Database credentials |
| `POSTGRES_PORT` | `5434` | Host port mapped to container `5432` |
| `DATABASE_URL` | compose-generated | Full database DSN |
| `CACHE_URL` | `redis://cache:6379/1` in Compose | Shared cache for throttling; omit locally to use in-memory cache |
| `JWT_ACCESS_HOURS` | `12` | Access token lifetime |
| `JWT_REFRESH_DAYS` | `7` | Refresh token lifetime |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed logins before lockout |
| `LOCK_MINUTES` | `15` | Lockout duration |
| `THROTTLE_ANON` | `120/min` | Anonymous request rate limit |
| `THROTTLE_USER` | `5000/hour` | Authenticated user rate limit |
| `THROTTLE_LOGIN` | `20/min` | Sign-in attempts per client IP |
| `CORS_ALLOWED_ORIGINS` | localhost origins | Allowed browser origins |
| `CSRF_TRUSTED_ORIGINS` | localhost origins | Trusted CSRF origins |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `SESSION_COOKIE_SAMESITE` / `CSRF_COOKIE_SAMESITE` | `Lax` | Cookie same-site policy |
| `SECURE_SSL_REDIRECT` | `false` | Force HTTPS redirects |
| `SECURE_HSTS_SECONDS` | `0` | HSTS max-age; set after HTTPS is verified |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` / `SECURE_HSTS_PRELOAD` | `false` | HSTS scope flags |
| `SECURE_REFERRER_POLICY` | `same-origin` | Referrer header policy |
| `HIGH_VALUE_QUOTE_THRESHOLD` | `50000` | Amount that triggers MD approval |
| `COMMISSION_PAYABLE_DAYS` | `30` | Commission payable window |
| `AUTOMATION_RENEWAL_DAYS` | `90` | Renewal reminder pipeline window |
| `AUTOMATION_RENEWAL_QUOTE_DAYS` | `60` | Create a draft renewal quotation inside this window |
| `AUTOMATION_COLLECTION_INTERVAL_DAYS` | `7` | Days between premium collection reminders |
| `AUTOMATION_INTERVAL_SECONDS` | `3600` | Scheduler run interval (default hourly) |
| `DEFAULT_FROM_EMAIL` | `no-reply@ibms.local` | Sender address for outgoing email |
| `EMAIL_BACKEND` | console backend | Use `django.core.mail.backends.smtp.EmailBackend` for live email |
| `EMAIL_HOST` / `EMAIL_PORT` | empty / `587` | SMTP server and port |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | empty | SMTP credentials |
| `EMAIL_USE_TLS` / `EMAIL_USE_SSL` | `true` / `false` | SMTP transport security |
| `SMS_GATEWAY_URL` | empty | HTTP gateway for SMS delivery; blank disables sending |
| `SMS_GATEWAY_TOKEN` | empty | Bearer token sent to the SMS gateway |
| `SMS_SENDER_ID` | `IBMS` | SMS sender name |
| `WAIT_FOR_DB` | `1` | Wait for the database at container start |
| `SEED_ON_START` | `1` | Run the idempotent seed command at start |
| `COLLECT_STATIC` | `1` | Run `collectstatic` at start |
| `SEED_PASSWORD` | `Password123!` | Password assigned to seeded demo users |
| `VITE_API_URL` | `/api` | Frontend API base URL baked at build time |
| `WEB_PORT` / `API_PORT` | `8080` / `4000` | Host ports |

## 5. Migrations

```bash
# generate after changing a model
docker compose exec api python manage.py makemigrations

# apply
docker compose exec api python manage.py migrate

# inspect
docker compose exec api python manage.py showmigrations
```

Commit new migration files together with the model change. Never edit an applied
migration; create a new one.

## 6. Seeding and roles

```bash
docker compose exec api python manage.py seed
```

The seed command is idempotent: it creates permissions, the ten roles, four branches,
ten demo users, insurance classes, insurers, products, clients, risks, policies,
premiums, payments, claims, endorsements, notes, remittances, tasks,
communications, approvals, documents and audit entries. Re-running it updates the
seed records rather than duplicating them.

To create a fresh empty database without demo data, set `SEED_ON_START=0`, remove
the volume, start the stack and run `createsuperuser`.

## 7. Automation scheduler

The `scheduler` Compose service runs `python manage.py run_automation` at startup and
then every `AUTOMATION_INTERVAL_SECONDS` (hourly by default). The command is
idempotent and safe to run more often: it advances renewal stages, creates one draft
renewal quotation per renewal, sends each stage reminder once, marks overdue
premiums, and sends collection reminders no more than once per configured interval.
Run it manually with:

```bash
docker compose exec api python manage.py run_automation
docker compose exec api python manage.py run_automation --date 2026-11-09
```

When running without Compose, call the command from host cron (for example hourly)
from the same environment as the API.

## 8. Backup and restore

Backup:

```bash
docker compose exec -T db pg_dump -U ibms -d ibms -Fc > ibms-$(date +%F).dump
docker run --rm -v ibms_ibms_media:/media -v "$PWD":/backup alpine \
  tar czf /backup/media-$(date +%F).tgz -C /media .
```

Restore:

```bash
docker compose stop api web
docker compose exec -T db dropdb -U ibms --if-exists ibms
docker compose exec -T db createdb -U ibms -O ibms ibms
docker compose exec -T db pg_restore -U ibms -d ibms < ibms-YYYY-MM-DD.dump
docker run --rm -v ibms_ibms_media:/media -v "$PWD":/backup alpine \
  tar xzf /backup/media-YYYY-MM-DD.tgz -C /media
docker compose start api web
```

Schedule backups outside business hours and test restores periodically.

## 9. Production checklist

- Set a long random `DJANGO_SECRET_KEY`; never ship the example value.
- Set `DJANGO_DEBUG=false` and a strict `DJANGO_ALLOWED_HOSTS`.
- Use strong database credentials; do not expose port `5434` publicly.
- Terminate TLS at a reverse proxy or load balancer; set `SECURE_SSL_REDIRECT=true`,
  `SESSION_COOKIE_SECURE=true` and `CSRF_COOKIE_SECURE=true`.
- After verifying HTTPS, enable HSTS with `SECURE_HSTS_SECONDS=31536000` and add
  `SECURE_HSTS_INCLUDE_SUBDOMAINS=true` / `SECURE_HSTS_PRELOAD=true` only when the
  whole domain is ready.
- Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the real web origin only.
- Keep Redis on the private Compose network; it stores shared login/API throttle counters.
- After the production environment variables are set, run
  `docker compose exec api python manage.py check --deploy` and aim for zero warnings.
- Run `SEED_ON_START=0` in production and create real users through the admin or
  Users module.
- Put `ibms_pgdata` and `ibms_media` on durable storage and back them up.
- Keep the Gunicorn worker count aligned with CPU/memory; put a request timeout and
  body-size limit at the proxy.
- Configure `EMAIL_BACKEND`/SMTP and `SMS_GATEWAY_URL` before enabling communication
  sending; the default console email backend does not deliver mail.
- Monitor `/api/health/`, container restarts and disk usage.
- Apply Django security updates and rebuild images on a regular cadence.

## 10. Troubleshooting

| Symptom | Check |
| --- | --- |
| Web shows 502 on `/api` | `docker compose logs api`; confirm the API health check is passing |
| API cannot connect to DB | Credentials in `.env`, `docker compose ps`, database health |
| Login fails for demo user | Run `docker compose exec api python manage.py seed`; verify `SEED_PASSWORD` |
| Account locked | Wait `LOCK_MINUTES`, or use **Unlock** in the Users module as an administrator |
| Communication shows Failed | Check client email/phone and the SMTP/SMS gateway settings |
| Migrations not applied | `docker compose exec api python manage.py showmigrations`; inspect entrypoint logs |
| Uploaded file 404 | Confirm the `ibms_media` volume is mounted and nginx proxies `/media/` |
| UI calls the wrong API URL | Rebuild `web` with the desired `VITE_API_URL` (it is baked at build time) |
| Port already in use | Change `WEB_PORT`, `API_PORT` or `POSTGRES_PORT` in `.env` |
| UI smoke test cannot find Chrome | Set `CHROME_PATH` or install Chrome/Chromium |
