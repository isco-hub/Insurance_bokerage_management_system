# API Reference

The IBMS API is a Django REST Framework JSON API. All application routes are under
`/api/`; there is no separate API version prefix. The browser SPA and the API are
served from different containers/origins, so CORS is configured for the web origin.

Base URLs:

- Docker: `http://localhost:4000/api`
- Local Django: `http://localhost:4000/api`
- Through nginx: `http://localhost:8080/api`

## 1. Authentication

Authentication uses SimpleJWT Bearer access tokens. Send the token on every
protected request:

```http
Authorization: Bearer <access-token>
Content-Type: application/json
```

### Sign in

```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "admin@ibms.local",
  "password": "Password123!"
}
```

Success (`200`):

```json
{
  "data": {
    "token": "<access-token>",
    "refresh": "<refresh-token>",
    "user": {
      "id": "…",
      "email": "admin@ibms.local",
      "full_name": "System Administrator",
      "role": "<role-uuid>",
      "role_name": "System Administrator",
      "role_code": "ADMIN",
      "permissions": ["clients:view", "clients:create", "…"]
    }
  }
}
```

Five failed attempts lock the account for 15 minutes by default. Invalid or inactive
accounts return `401`; an account that needs a different role/permission returns
`403`.

### Other auth routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/auth/me/` | Current user, role, branch and permissions |
| `POST` | `/api/auth/logout/` | Blacklist a refresh token; body `{"refresh":"…"}` |
| `POST` | `/api/auth/change-password/` | Body `currentPassword`, `newPassword` |
| `GET` | `/api/health/` | Unauthenticated health and database check |

Example sign-in with cURL:

```bash
TOKEN=$(curl -sS -X POST http://localhost:4000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@ibms.local","password":"Password123!"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["token"])')

curl -sS http://localhost:4000/api/clients/ \
  -H "Authorization: Bearer $TOKEN"
```

## 2. Response conventions

### Lists

List endpoints are paginated unless documented otherwise:

```json
{
  "data": [ { "id": "…" } ],
  "meta": { "page": 1, "pageSize": 20, "total": 57, "totalPages": 3 }
}
```

Query parameters:

| Parameter | Example | Meaning |
| --- | --- | --- |
| `page` | `2` | Page number, starting at 1 |
| `pageSize` | `50` | Page size; default 20, maximum 200 |
| `search` | `search=UAP` | Full-text search over the endpoint's configured fields |
| `ordering` | `ordering=-created_at` | Sort field; `-` means descending |
| filters | `status=ACTIVE&branch=<uuid>` | Endpoint-specific exact-match filters |

Filter names are listed in the endpoint table and detailed in
[`03-data-dictionary.md`](03-data-dictionary.md).

### Single records and writes

Create, retrieve and update responses are wrapped:

```json
{ "data": { "id": "…", "…": "…" } }
```

- `POST` list create → `201` with `{data}` and a `Location` header.
- `GET` detail → `200` with `{data}`.
- `PUT` / `PATCH` detail → `200` with `{data}`.
- `DELETE` detail → `204` with no body.
- Custom actions → `200` or `201` with `{data}`.

### Errors

Errors have a consistent top-level shape:

```json
{
  "statusCode": 400,
  "message": "Validation failed",
  "details": { "end_date": ["End date must be after the start date"] }
}
```

`message` is a string or a field message. `details` contains the original DRF
validation errors. Custom business errors use `{statusCode, message}`.

| Status | Meaning |
| --- | --- |
| `400` | Validation or invalid workflow transition |
| `401` | Missing, expired or invalid token; invalid credentials |
| `403` | Authenticated but missing `module:action` permission, or self-approval |
| `404` | Record or report/route not found |
| `409` | Database conflict such as a duplicate unique value |
| `429` | Throttle limit exceeded; retry after the window |
| `503` | Health check cannot reach the database |

## 3. Permissions and branch scoping

Every protected view computes a permission such as `clients:view`,
`quotations:edit` or `claims:approve`. A user must hold that exact permission through
their role, unless the role is `ADMIN`, which bypasses the matrix. Custom actions use
higher permissions where appropriate:

| Action | Required permission |
| --- | --- |
| Quotation select | `quotations:edit` |
| Quotation accept / create policy | `policies:create` |
| Endorsement decide | `endorsements:approve` |
| Commission mark paid | `commissions:edit` |
| Commission reconcile | `commissions:approve` |
| Remittance mark paid | `remittances:edit` |
| Remittance reconcile | `remittances:approve` |
| Remittance generate | `remittances:create` |
| Claim settle | `claims:approve` |
| Task complete | `tasks:edit` |
| Approval decide | `approvals:approve` |

Roles `BRANCH`, `BROKER` and `SERVICE` are branch-scoped. For branch-scoped views the
queryset is filtered to the user's `branch` before filters/search/ordering apply.
Users without a branch assignment in those roles are not filtered by this rule.

## 4. Endpoint catalogue

### 4.1 Accounts and administration

| Endpoint | Module | Methods | Filter fields | Notes |
| --- | --- | --- | --- | --- |
| `/api/branches/` | `branches` | CRUD | `is_active` | Soft delete; search code/name/email |
| `/api/roles/` | `roles` | CRUD | `is_system` | Includes assigned permissions |
| `/api/permissions/` | `roles` | Read-only | `module`, `action` | Unpaginated; used by role form |
| `/api/users/` | `users` | CRUD | `role`, `branch`, `is_active` | Password optional on update; soft delete |
| `/api/audit-logs/` | `audit` | Read-only | `action`, `module`, `user`, `entity_type` | Immutable audit trail |

### 4.2 Customer Relationship

| Endpoint | Module | Methods | Filter fields | Notes |
| --- | --- | --- | --- | --- |
| `/api/clients/` | `clients` | CRUD | `client_type`, `kyc_status`, `branch`, `relationship_manager`, `is_active` | Client number auto; soft delete; branch-scoped |
| `/api/client-contacts/` | `clients` | CRUD | `client`, `is_primary` | Search name/email/phone |
| `/api/client-directors/` | `clients` | CRUD | `client` | Search name/national ID/email |
| `/api/insurers/` | `insurers` | CRUD | `is_active` | Soft delete; search code/name/email/phone |
| `/api/insurer-contacts/` | `insurers` | CRUD | `insurer`, `is_primary` | Search name/email/phone |
| `/api/insurer-branches/` | `insurers` | CRUD | `insurer`, `is_active` | Search name/address/email |
| `/api/insurance-classes/` | `products` | CRUD | `category`, `is_active` | Search code/name |
| `/api/products/` | `products` | CRUD | `insurer`, `insurance_class`, `is_active` | Soft delete; search code/name |

### 4.3 Brokerage Operations

| Endpoint | Module | Methods | Filter fields | Notes |
| --- | --- | --- | --- | --- |
| `/api/risks/` | `risks` | CRUD | `client`, `status`, `category` | Risk number auto; branch-scoped; returns motor details |
| `/api/motor-details/` | `motor` | CRUD | `risk` | Branch-scoped through risk client branch |
| `/api/quotations/` | `quotations` | CRUD + `select`, `accept` | `client`, `product`, `risk`, `status`, `branch`, `broker`, `selected_insurer` | Returns nested `insurer_quotes` |
| `/api/insurer-quotes/` | `quotations` | CRUD | `quotation`, `insurer`, `status` | Marking `RECEIVED` advances the parent quotation |
| `/api/policies/` | `policies` | CRUD | `client`, `insurer`, `product`, `status`, `branch`, `broker` | Branch-scoped |
| `/api/endorsements/` | `endorsements` | CRUD + `decide` | `policy`, `status`, `type` | Branch-scoped |
| `/api/renewals/` | `renewals` | CRUD + `outcome` | `policy`, `status`, `stage_days`, `handled_by` | Branch-scoped |

### 4.4 Finance

| Endpoint | Module | Methods | Filter fields | Notes |
| --- | --- | --- | --- | --- |
| `/api/premiums/` | `premiums` | CRUD | `policy`, `status` | `amount_paid`/`paid_at` read-only; balance calculated |
| `/api/invoices/` | `invoices` | CRUD | `client`, `policy`, `status` | Invoice number, totals and balance calculated |
| `/api/payments/` | `payments` | CRUD | `client`, `policy`, `invoice`, `method`, `status` | Creation allocates to premiums/invoices |
| `/api/credit-debit-notes/` | `notes` | CRUD | `client`, `policy`, `note_type`, `status` | Number prefix `CRN` or `DBN` |
| `/api/commissions/` | `commissions` | CRUD + `mark_paid`, `reconcile` | `policy`, `insurer`, `broker`, `status` | Branch-scoped |
| `/api/remittances/` | `remittances` | CRUD + `mark_paid`, `reconcile`, `generate` | `insurer`, `branch`, `status` | Generate is a collection action |

### 4.5 Claims and workspace

| Endpoint | Module | Methods | Filter fields | Notes |
| --- | --- | --- | --- | --- |
| `/api/claims/` | `claims` | CRUD + `settle` | `policy`, `client`, `status`, `handled_by` | Branch-scoped; settle requires `claims:approve` |
| `/api/documents/` | `documents` | CRUD | `entity_type`, `entity_id`, `category`, `is_current` | Multipart upload; `file` required on create |
| `/api/communications/` | `communications` | CRUD + `send` | `client`, `channel`, `status`, `related_entity_type`, `related_entity_id` | Email/SMS/phone/meeting/letter/portal |
| `/api/tasks/` | `tasks` | CRUD + `complete` | `assigned_to`, `status`, `priority`, `related_entity_type` | Complete sets status and timestamp |
| `/api/approvals/` | `approvals` | CRUD + `decide`, `review` | `status`, `type`, `entity_type`, `requested_by`, `approver` | `review` returns the approval and linked entity; requester cannot decide own request |

### 4.6 Reporting and search

| Method | Endpoint | Permission | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/dashboard/` | `dashboard:view` | Eight KPI groups, branch-scoped for branch roles |
| `GET` | `/api/reports/<report>/` | `reports:view` | Report keys use hyphens |
| `GET` | `/api/search/?q=term` | `search:view` | Minimum 2 characters; returns grouped results |
| `GET` | `/api/health/` | Public | `200` healthy or `503` degraded |

Report keys:

`premium-production`, `business-mix`, `commission`, `commission-ageing`,
`commission-statement`, `remittance-reconciliation`, `debtors-ageing`,
`quotation-conversion`, `claim-analysis`, `business-by-client`, `policy-register`,
`premium-collections`, `outstanding-premiums`, `outstanding-debtors`, `claims`,
`renewals`, `staff-performance`, `expiring-policies`, `lost-business`,
`accounting`, `audit-summary`.

Every report can be downloaded as CSV with
`GET /api/reports/<report>/export/` (same filters; requires `reports:view`).

Most reports accept `from` and `to` ISO dates (`YYYY-MM-DD`). Some add `status` or
`days`; see the backend `reporting/views.py` handlers or the report UI. Unknown report
keys return `404 {"statusCode":404,"message":"Unknown report"}`.

## 5. Workflow actions

### 5.1 Quotation: select an insurer

`POST /api/quotations/{id}/select/`

```json
{ "insurer_id": "<insurer-uuid>" }
```

The insurer must already have a quote with status `RECEIVED`. The quotation's status
becomes `SELECTED` and its premium/taxes are copied from the quote. Requires
`quotations:edit`.

### 5.2 Quotation: accept and create a policy

`POST /api/quotations/{id}/accept/`

```json
{
  "start_date": "2026-11-01",
  "end_date": "2027-10-31",
  "payment_frequency": "ANNUAL",
  "notes": "Accepted by client"
}
```

The quotation must be selected, not declined, not expired, and approved if its total
premium is at or above `HIGH_VALUE_QUOTE_THRESHOLD`. Returns `201` with the created
policy in `{data}`. Requires `policies:create`.

### 5.3 Endorsement decision

`POST /api/endorsements/{id}/decide/`

```json
{ "status": "APPROVED" }
```

Allowed values are `APPROVED` and `REJECTED`. The requester cannot approve their own
endorsement. Approval creates a credit/debit note when a premium adjustment exists.
Requires `endorsements:approve`.

### 5.4 Renewal outcome

`POST /api/renewals/{id}/outcome/`

```json
{ "status": "LOST", "lost_reason": "Client moved to another broker", "notes": "Follow up next year" }
```

Allowed values are `WON`, `LOST` and `LAPSED`.

### 5.5 Commission actions

`POST /api/commissions/{id}/mark_paid/` sets status `PAID` and the paid timestamp.

`POST /api/commissions/{id}/reconcile/` sets status `RECONCILED` and ensures a paid
timestamp. Reconcile requires `commissions:approve`.

### 5.6 Remittance actions

`POST /api/remittances/{id}/mark_paid/`

```json
{ "reference": "BANK-2026-001" }
```

`POST /api/remittances/{id}/reconcile/` sets status `RECONCILED`.

`POST /api/remittances/generate/` creates a draft advice for an insurer and period:

```json
{
  "insurer": "<insurer-uuid>",
  "period_from": "2026-10-01",
  "period_to": "2026-10-31",
  "branch": "<optional-branch-uuid>"
}
```

Returns `201` with the calculated gross premium, retained commission, taxes and net
amount. Requires `remittances:create`.

### 5.7 Claim settlement

`POST /api/claims/{id}/settle/`

```json
{
  "paid_amount": 500.00,
  "recovered_amount": 0,
  "notes": "Settled by insurer"
}
```

The claim status becomes `SETTLED` and `settled_at` is recorded. Requires
`claims:approve`.

### 5.8 Task complete

`POST /api/tasks/{id}/complete/` with no required body. Status becomes `DONE`.

### 5.9 Approval review and decision

`GET /api/approvals/{id}/review/` returns the approval together with the serialized
linked entity (`Quotation`, `Policy`, `Claim`, `Client`, `Commission`, `Payment`,
`Invoice`, `CreditDebitNote` or `Remittance`) when it is still available. This is the
context used by the approval review screen.

`POST /api/approvals/{id}/decide/`

```json
{ "status": "APPROVED", "comments": "Approved by management" }
```

Allowed values are `APPROVED` and `REJECTED`. The requester cannot decide their own
request. Approved endorsement and claim-settlement approvals update the linked
record. Requires `approvals:approve`.

## 6. Documents and files

Create a document with `multipart/form-data`:

```bash
curl -sS -X POST http://localhost:4000/api/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -F 'entity_type=policy' \
  -F 'entity_id=<policy-uuid>' \
  -F 'name=Signed policy schedule' \
  -F 'category=Policy document' \
  -F 'file=@/path/to/schedule.pdf'
```

Only `entity_type`, `entity_id`, `name` and `file` are required. `mime_type`, `size`,
`version`, `is_current`, `uploaded_by`, `file_url` and `file_name` are read-only.
A new upload for the same entity and document name becomes the current version. Files are served from
`/media/` through nginx in the Docker stack.

## 7. Notes and limits

- UUIDs are used as primary keys; send UUID strings, not integers.
- Monetary decimal values are JSON numbers, not strings.
- Dates use `YYYY-MM-DD`; timestamps use ISO-8601 with timezone.
- Soft-deleted master data remains visible with `is_active: false`; a normal
  `DELETE` does not remove the database row.
- Pagination defaults to 20 and is capped at 200.
- Use `ordering=-created_at` (not `sort`) for sorting.
- Branch-scoped permissions are enforced on the server; hiding a menu item in the UI
  is not a security boundary.
- Rate limits are enabled by default: anonymous traffic `120/min`, authenticated users
  `5000/hour`, and sign-in attempts `20/min` per client IP. Health checks are exempt.
  Override them with `THROTTLE_ANON`, `THROTTLE_USER` and `THROTTLE_LOGIN`. Exceeding a
  limit returns `429`.
<!-- 2026-11-11T15:06:09Z payment API -->
<!-- 2026-11-11T15:06:10Z reporting API -->
<!-- 2026-11-11T15:06:11Z policy endpoints -->
