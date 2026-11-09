# IBMS — User Roles and Permissions Matrix

Version 1.0 · Prepared for management review

Access control is permission-based. Each permission is a `(module, action)` pair;
roles are bundles of permissions. The API enforces permissions on every request and
the UI hides actions the current user cannot perform.

Legend for actions: **V** view · **C** create · **E** edit · **A** approve ·
**D** delete/deactivate · **R** generate reports.

---

## 1. Role definitions

| Code | Role | Responsibility summary |
| --- | --- | --- |
| ADMIN | System Administrator | Full system administration, users, roles, branches, configuration, audit integrity |
| MD | Managing Director | Executive oversight, high-value approvals, all management reporting |
| OPS | Operations Manager | Operations supervision, workflow approvals, operational performance |
| BRANCH | Branch Manager | Branch performance, branch-level operations and approvals |
| BROKER | Broker / Relationship Manager | Client acquisition, risk capture, quotations, policies, renewals |
| UNDERWRITING | Underwriting Officer | Product/insurer terms, quote responses, policy schedules, endorsements |
| CLAIMS | Claims Officer | Claim registration, assessment, reserves, settlement processing |
| FINANCE | Finance Officer | Premiums, receipts, invoices, commissions, remittances, reconciliation |
| SERVICE | Customer Service Officer | Client data, documents, communication, task follow-up |
| AUDITOR | Auditor | Read-only assurance, audit trail and compliance reporting |

## 2. Permissions by module

### 2.1 Core administration

| Module | Action | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dashboard | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Search | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Branches | V | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Branches | C/E/D | ✓ |  |  |  |  |  |  |  |  |  |
| Users | V | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  | ✓ |
| Users | C/E/D | ✓ |  |  |  |  |  |  |  |  |  |
| Roles & permissions | V | ✓ | ✓ |  |  |  |  |  |  |  | ✓ |
| Roles & permissions | C/E/D | ✓ |  |  |  |  |  |  |  |  |  |
| Audit trail | V | ✓ | ✓ | ✓ |  |  |  |  |  |  | ✓ |
| Audit trail | R | ✓ | ✓ |  |  |  |  |  |  |  | ✓ |
| Approvals | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |
| Approvals | A | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  |  |

### 2.2 Clients, insurers and products

| Module | Action | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Clients | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Clients | C | ✓ |  | ✓ | ✓ | ✓ |  |  |  | ✓ |  |
| Clients | E | ✓ |  | ✓ | ✓ | ✓ |  |  |  | ✓ |  |
| Clients | D | ✓ |  |  |  |  |  |  |  |  |  |
| Clients | R | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | ✓ |
| Insurers | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Insurers | C/E | ✓ |  | ✓ |  |  |  |  |  |  |  |
| Insurers | D | ✓ |  |  |  |  |  |  |  |  |  |
| Products & classes | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Products & classes | C/E | ✓ |  | ✓ |  |  | ✓ |  |  |  |  |
| Products & classes | D | ✓ |  |  |  |  |  |  |  |  |  |
| Products & classes | R | ✓ | ✓ | ✓ |  |  |  |  |  |  | ✓ |

### 2.3 Brokerage operations

| Module | Action | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Risks | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | ✓ |
| Risks | C/E | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  |  |
| Risks | D | ✓ |  |  |  |  |  |  |  |  |  |
| Motor details | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | ✓ |
| Motor details | C/E | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  |  |
| Motor details | D | ✓ |  |  |  |  |  |  |  |  |  |
| Quotations | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ |
| Quotations | C | ✓ |  | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| Quotations | E | ✓ |  | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| Quotations | A | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| Quotations | D | ✓ |  |  |  |  |  |  |  |  |  |
| Quotations | R | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | ✓ |
| Policies | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Policies | C/E | ✓ |  | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| Policies | D | ✓ |  |  |  |  |  |  |  |  |  |
| Policies | R | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | ✓ |
| Endorsements | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ |  | ✓ |
| Endorsements | C/E | ✓ |  | ✓ | ✓ |  | ✓ |  |  |  |  |
| Endorsements | A | ✓ | ✓ | ✓ | ✓ |  |  |  |  |  |  |
| Renewals | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ | ✓ |
| Renewals | C/E | ✓ |  | ✓ | ✓ | ✓ |  |  |  | ✓ |  |
| Renewals | R | ✓ | ✓ | ✓ | ✓ | ✓ |  |  |  |  | ✓ |

### 2.4 Financial management

| Module | Action | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Premiums | V | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | ✓ |
| Premiums | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Premiums | R | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Invoices | V | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | ✓ |
| Invoices | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Invoices | D | ✓ |  |  |  |  |  |  |  |  |  |
| Payments / receipts | V | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | ✓ |
| Payments / receipts | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Payments / receipts | D | ✓ |  |  |  |  |  |  |  |  |  |
| Credit/debit notes | V | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Credit/debit notes | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Commissions | V | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | ✓ |
| Commissions | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Commissions | A | ✓ | ✓ | ✓ |  |  |  |  | ✓ |  |  |
| Commissions | R | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Remittances | V | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Remittances | C/E | ✓ |  |  |  |  |  |  | ✓ |  |  |
| Remittances | A | ✓ | ✓ | ✓ |  |  |  |  | ✓ |  |  |
| Remittances | R | ✓ | ✓ | ✓ |  |  |  |  | ✓ |  | ✓ |

### 2.5 Claims and collaboration

| Module | Action | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claims | V | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ |
| Claims | C/E | ✓ |  | ✓ | ✓ |  |  | ✓ |  |  |  |
| Claims | A | ✓ | ✓ | ✓ |  |  |  |  |  |  |  |
| Claims | R | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |  | ✓ |
| Documents | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Documents | C/E | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| Documents | D | ✓ |  |  |  |  |  |  |  |  |  |
| Communications | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Communications | C/E | ✓ |  | ✓ | ✓ | ✓ |  | ✓ |  | ✓ |  |
| Tasks | V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tasks | C/E | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| Tasks | D | ✓ |  |  |  |  |  |  |  |  |  |

### 2.6 Management reporting

| Report family | ADMIN | MD | OPS | BRANCH | BROKER | UNDERWRITING | CLAIMS | FINANCE | SERVICE | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Business reports | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  | ✓ |
| Financial reports | ✓ | ✓ | ✓ | ✓ |  |  |  | ✓ |  | ✓ |
| Claims reports | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |  | ✓ |
| Operational reports | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Audit reports | ✓ | ✓ |  |  |  |  |  |  |  | ✓ |

## 3. Module/action permission codes

The seed grants the following codes (all combinations are created in `permissions`;
only the ones below are attached to roles).

```
dashboard:view, search:view
branches:view, branches:create, branches:edit, branches:delete
users:view, users:create, users:edit, users:delete
roles:view, roles:create, roles:edit, roles:delete
audit:view, audit:report
approvals:view, approvals:approve
clients:view, clients:create, clients:edit, clients:delete, clients:report
insurers:view, insurers:create, insurers:edit, insurers:delete
products:view, products:create, products:edit, products:delete, products:report
risks:view, risks:create, risks:edit, risks:delete
motor:view, motor:create, motor:edit, motor:delete
quotations:view, quotations:create, quotations:edit, quotations:approve, quotations:delete, quotations:report
policies:view, policies:create, policies:edit, policies:delete, policies:report
endorsements:view, endorsements:create, endorsements:edit, endorsements:approve
renewals:view, renewals:create, renewals:edit, renewals:report
premiums:view, premiums:create, premiums:edit, premiums:report
invoices:view, invoices:create, invoices:edit, invoices:delete
payments:view, payments:create, payments:edit, payments:delete
notes:view, notes:create, notes:edit
commissions:view, commissions:create, commissions:edit, commissions:approve, commissions:report
remittances:view, remittances:create, remittances:edit, remittances:approve, remittances:report
claims:view, claims:create, claims:edit, claims:approve, claims:report
documents:view, documents:create, documents:edit, documents:delete
communications:view, communications:create, communications:edit
tasks:view, tasks:create, tasks:edit, tasks:delete
reports:view
```

## 4. Enforcement rules

1. **Server-side is authoritative.** The API validates the JWT, loads the permission
   list, and rejects requests without the required `(module, action)`.
2. **UI reflects permissions.** Navigation items and action buttons are hidden or
   disabled when the permission is absent.
3. **Branch scoping.** Non-group roles (`BRANCH`, `BROKER`, `SERVICE`) are scoped to
   their branch for list endpoints; group roles (`ADMIN`, `MD`, `OPS`, `AUDITOR`)
   see all branches.
4. **Segregation of duties.** A user cannot approve their own request; approvers must
   hold `approvals:approve` and the module's `approve` permission.
5. **Data-level controls.** Auditors are read-only. Deletes are soft deletes for
   records with financial history and are restricted to administrators.
6. **Session controls.** Accounts lock after five consecutive failed logins for 15
   minutes (configurable); all sessions expire with the JWT.
