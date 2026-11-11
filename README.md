# Insurance Brokerage Management System (IBMS)

A secure, containerised, web-based platform that automates the core operations of an
insurance brokerage: client relationship management, insurer and product registers,
risk capture, multi-insurer quotations, policy administration, premium collection,
commission accounting, insurer remittances, claims, renewals, approvals, reporting
and audit.

Developed from the business requirements in
`Insurance Brokerage Management system.docx`. Monetary values use Ugandan
shillings (`UGX`, displayed as `USh`) and the default timezone is `Africa/Kampala`.

## Technology stack

| Layer | Selection | Why |
| --- | --- | --- |
| Frontend | React 19 + TypeScript (Vite) | Fast typed SPA, reusable module-driven UI, Recharts dashboards |
| Backend | Django 5.2 + Django REST Framework 3.16 | Mature ORM, explicit permissions, serializers and browsable API |
| Auth | SimpleJWT + Django password hashing | Stateless Bearer tokens, refresh flow, server-side RBAC |
| Database | PostgreSQL 16 | Strong constraints, decimal accuracy, JSONB for risk/asset data, analytical SQL |
| Cache / rate limits | Redis 7 | Shared DRF throttle counters across Gunicorn workers |
| Runtime | Docker + Docker Compose | Reproducible local/production deployment with persistent volumes |

A detailed evaluation of Django, Laravel and NestJS is in
[`docs/05-architecture-and-stack.md`](docs/05-architecture-and-stack.md).

## Repository layout

```
IBMS/
├── backend/                # Django project and apps
│   ├── accounts/           # users, roles, permissions, branches, audit, auth
│   ├── crm/                # clients, insurers, classes, products
│   ├── operations/         # risks, motor, quotations, policies, endorsements, renewals
│   ├── finance/            # premiums, invoices, payments, notes, commissions, remittances
│   ├── claims/             # claims workflow
│   ├── workspace/          # documents, communications, tasks, approvals
│   ├── reporting/          # dashboard, reports, global search, health
│   ├── common/             # permissions, pagination, numbering, audit, viewset base
│   └── ibms/               # settings, URLs, WSGI/ASGI
├── frontend/               # React + TypeScript SPA (Vite)
├── docs/                   # Process, ERD, data dictionary, RBAC, architecture and guides
├── scripts/                # API and browser smoke tests
├── docker-compose.yml
├── .env.example
└── README.md
```

## Preliminary deliverables (management review pack)

1. [Business process analysis and workflows](docs/01-business-process-analysis.md)
2. [Entity Relationship Diagram](docs/02-erd.md)
3. [Database tables and data dictionary](docs/03-data-dictionary.md)
4. [User roles and permissions matrix](docs/04-roles-permissions-matrix.md)
5. [Architecture, backend evaluation and security design](docs/05-architecture-and-stack.md)

Delivery and operations documentation:

- [Installation and deployment guide](docs/INSTALLATION.md)
- [User guide](docs/USER_GUIDE.md)
- [Testing guide and results](docs/TESTING.md)
- [API reference](docs/API_REFERENCE.md)

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build -d
```

| Service | URL |
| --- | --- |
| Landing page / web application | http://localhost:8080 |
| API | http://localhost:4000/api |
| API health | http://localhost:4000/api/health/ |
| PostgreSQL | localhost:5434 (host) → 5432 (container) |
| Automation scheduler | background worker, runs hourly |

The API entrypoint waits for PostgreSQL, applies Django migrations, collects static
files and (by default) runs the idempotent seed command. Set `SEED_ON_START=0` in
`.env` to skip seeding. A separate scheduler container runs renewal, quotation and
premium collection automation hourly; set `AUTOMATION_INTERVAL_SECONDS` to change
that interval.

Demo users are created by the seed (password `Password123!` unless overridden by
`SEED_PASSWORD` in `.env`):

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

## Smoke tests

With the Docker stack running and seeded:

```bash
docker compose exec -T api python manage.py test  # backend unit and API tests
./scripts/smoke_api.sh                            # API, RBAC and report checks
node scripts/smoke_ui.mjs                         # headless Chrome UI checks
```

The UI script uses `playwright-core` from `frontend/node_modules` and a locally
installed Chrome/Chromium (`CHROME_PATH` can override detection). See
[`docs/TESTING.md`](docs/TESTING.md) for details.

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md) for local (non-Docker) setup,
migrations, seeding, backups and troubleshooting.
<!-- 2026-11-11T15:06:10Z compose init -->
