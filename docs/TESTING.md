# Testing Guide and Results

IBMS uses three layers of verification: Django framework checks, an API smoke test
and a browser smoke test. The smoke tests are intentionally black-box: they exercise
the running Docker stack the same way a user would, so they catch wiring, seeding,
authentication, routing, rendering and basic workflow problems that unit tests alone
would miss.

A Django `TestCase` suite now covers authentication, lockout, RBAC, branch scoping,
soft delete, quotation acceptance, payment allocation, claim settlement and
reporting. The browser and API smoke tests remain the deployment gate.

## 1. Test environment

The recorded results below were produced on 9 November 2026 with:

- Docker Compose services `db`, `cache`, `api`, `scheduler` and `web` running;
- PostgreSQL 16 with the idempotent demo seed;
- API at http://localhost:4000/api and web at http://localhost:8080;
- API image using Python 3.12, Django 5.2.5 and DRF 3.16.1;
- frontend built with React 19/Vite 7 and served by nginx;
- headless Chrome 154 controlled through `playwright-core` 1.65.

Always test against a seeded database. If you have changed models, apply migrations
and reseed before running the tests:

```bash
docker compose up -d --build
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed
```

## 2. Django checks and unit tests

```bash
docker compose exec api python manage.py check
docker compose exec api python manage.py makemigrations --check --dry-run
docker compose exec api python manage.py showmigrations
docker compose exec -T api python manage.py test --keepdb
```

Expected:

- `System check identified no issues (0 silenced).`
- `No changes detected` from `makemigrations --check` (models and migrations agree).
- All migrations show `[X]`.
- The unit suite reports `Ran 30 tests` and `OK`.

The unit suite lives beside each app (`accounts/tests.py`, `operations/tests.py`,
`finance/tests.py`, `claims/tests.py`, `reporting/tests.py`) with shared fixtures in
`common/testing.py`. It covers:

- valid login, invalid password, account lockout and unauthenticated access;
- permission denial, ADMIN bypass, branch-scoped lists and soft deletion;
- quotation insurer selection and acceptance, including threshold approval and
  expiry rejection;
- policy bundle creation (invoice, premium schedule, commission and renewal);
- confirmed and pending payment allocation, plus full and partial refunds;
- policy cancellation, renewal lapse and pending-commission cancellation;
- failed-login unlock;
- email delivery, unconfigured SMS failure and report CSV export;
- claim settlement;
- dashboard KPIs, all specialized reports, unknown-report 404 and public health;
- approval review context and permission to decide;
- renewal automation, automatic renewal quotations, collection reminders and
  fallback tasks when delivery fails.

Recorded result on 9 November 2026: **30 of 30 tests passed**.

## 3. API smoke test

```bash
./scripts/smoke_api.sh
```

The script signs in as the seeded administrator, stores the JWT in memory and checks:

1. health endpoint and database status;
2. administrator login and token issuance;
3. current-user profile;
4. dashboard payload;
5. clients, policies, quotations, payments, claims, tasks and approvals lists;
6. a client detail endpoint;
7. approval review context for a pending request;
8. all seven specialized reports and the existing core reports;
9. CSV report export;
10. global search;
11. rejection of an invalid password.

The list checks assert the `{data, meta}` envelope shape. The script uses `curl`
plus `python3` for small JSON assertions, so it works without `jq`.

Expected final line:

```text
All API smoke checks passed.
```

Recorded result on 9 November 2026: **26 of 26 checks passed**, including client
detail, CSV export and invalid-login rejection.

## 4. Browser smoke test

Prerequisites:

- the web and API containers are running;
- `frontend/node_modules` exists (`npm ci` was run in `frontend`);
- Chrome/Chromium is installed. The script auto-detects `/usr/bin/google-chrome`,
  `/usr/bin/chromium`, `/usr/bin/chromium-browser` and common macOS paths. Set
  `CHROME_PATH=/path/to/chrome` to override.

```bash
node scripts/smoke_ui.mjs
```

The script launches headless Chrome, signs in as `admin@ibms.local` and checks:

- the dashboard renders eight KPI cards;
- all 30 module routes render the expected page title and at least one data row;
- the global search page returns grouped results;
- all 21 report pages render without a load error;
- the client create modal opens and contains 23 fields;
- a record detail page renders documents and communications sections;
- the approval review page loads the linked transaction and decision form;
- the account page renders the password form;
- report **Export CSV** downloads a `.csv` file.

Recorded result on 9 November 2026: **0 issues**, with these row counts:

| Route | Rows | Route | Rows |
| --- | ---: | --- | ---: |
| Clients | 10 | Quotations | 10 |
| Client Contacts | 10 | Insurer Quotes | 17 |
| Client Directors | 6 | Policies | 8 |
| Insurers | 7 | Endorsements | 3 |
| Insurer Contacts | 7 | Renewals | 8 |
| Insurer Branches | 7 | Premiums | 20 |
| Products | 10 | Invoices | 8 |
| Insurance Classes | 9 | Payments | 5 |
| Risks | 8 | Credit / Debit Notes | 2 |
| Motor Details | 2 | Commissions | 8 |
| Tasks | 6 | Remittances | 2 |
| Approvals | 2 | Claims | 6 |
| Documents | 2 | Communications | 16 |
| Users | 10 | Roles & Permissions | 10 |
| Branches | 4 | Audit Trail | 20 |

## 5. Workflow tests performed

### 5.1 Authentication and RBAC

- Administrator login succeeds and returns access and refresh tokens.
- Invalid password returns 401 and is rejected by the smoke test.
- `/auth/me/` returns the authenticated user, role, branch and permissions.
- Users without a required `module:action` permission receive 403.
- Branch-scoped roles only receive records for their own branch.
- ADMIN bypasses the permission matrix as designed.

### 5.2 Create, edit and delete

- Created each resource through the UI and API where applicable.
- Edited clients, users, documents, products, insurers and operational records.
- Confirmed blank password on user edit keeps the existing password.
- Confirmed document file is required on create but optional on edit.
- Confirmed master-data delete deactivates (`is_active=false`) rather than removing
  the row; the row remains visible and can be reactivated.

### 5.3 Quotation to policy

- Created a temporary quotation and an insurer quote marked **Received**.
- Selected the insurer through the quotation row action.
- Accepted the quotation and confirmed a policy was created.
- Temporary quotation, policy and invoice records were removed afterwards.

### 5.4 Claim settlement

- Created a temporary claim linked to an existing policy/client.
- Settled it through the claim row action with a paid amount.
- Confirmed status `SETTLED`, paid amount and settlement timestamp.
- Temporary claim was removed afterwards.

### 5.5 Reporting, search and UI reliability

- All twenty-one report routes returned data without console/page errors.
- Report route names are hyphenated and match the backend handlers.
- Global search returns clients, policies, quotations, claims and insurers.
- Dashboard renders KPI cards after login.
- Approval review loads the linked entity and allows a permitted user to decide.
- Automation creates one renewal quotation and one reminder per stage, and marks
  overdue premiums while sending collection reminders no more than weekly.
- Favicon loads without a 404.

## 6. Manual regression checklist

Run this after changing permissions, serializers or core workflows:

- [ ] Sign in as each of the ten seeded roles and confirm the sidebar matches the role.
- [ ] Create and edit a client; confirm branch scoping for a branch user.
- [ ] Create a risk and a motor detail linked to it.
- [ ] Create a quotation, add two insurer quotes, select one and accept it.
- [ ] Confirm policy, premium schedule and commission records were generated.
- [ ] Record a payment and confirm premium/invoice balances update.
- [ ] Partially refund a confirmed payment and confirm invoice/premium reversal.
- [ ] Create an endorsement, approve it as a different user and confirm the note.
- [ ] Cancel a policy with an effective date/reason and confirm renewals/commissions.
- [ ] Create a claim and settle it.
- [ ] Mark a commission paid and reconcile it as an authorised user.
- [ ] Generate a remittance, mark it paid and reconcile it with the exact net amount.
- [ ] Send an email communication and confirm its status becomes Sent.
- [ ] Open all twenty-one reports, apply a date filter and export a CSV.
- [ ] Open a record detail page and confirm linked documents/communications.
- [ ] Change a password from Account settings and unlock a locked user as admin.
- [ ] Search globally for a known policy number.
- [ ] Deactivate and reactivate a master-data record.
- [ ] Confirm an auditor can read but not modify operational records.
- [ ] Confirm the audit trail records logins, creates, updates and approvals.

## 7. Build and static verification

```bash
cd frontend
npm run build
```

This runs `tsc -b` followed by `vite build`. Route-level lazy loading and manual
vendor/chart chunks keep the entry bundle at about 351 kB before gzip; charts load in
a separate 430 kB chunk only when needed. The build completes without a chunk-size
warning.

Backend syntax and import verification happens through `manage.py check` and the API
smoke test.

## 8. Troubleshooting test failures

| Symptom | Likely cause / fix |
| --- | --- |
| API smoke cannot log in | Seed has not run or `SEED_PASSWORD` differs; run `manage.py seed` |
| UI smoke reports zero rows | Seed data missing or branch-scoped demo user used; the script uses admin |
| UI smoke cannot launch Chrome | Set `CHROME_PATH` or install Chrome/Chromium |
| `playwright-core` not found | Run `npm ci` in `frontend` |
| Report check fails | Inspect `docker compose logs api`; confirm the hyphenated route exists |
| API returns 429 | A throttle limit was reached; wait for the window or adjust `THROTTLE_*` |
| 502 from web | Wait for API health, then `docker compose logs api` |
| `makemigrations --check` fails | Run `makemigrations`, review and commit the migration |
