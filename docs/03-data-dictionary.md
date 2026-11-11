# IBMS — Database Tables and Data Dictionary

Version 1.0 · PostgreSQL 16 · Implemented with Django ORM and Django migrations

Conventions:

- Every table has `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- Every mutable table has `created_at` and `updated_at` (`TIMESTAMPTZ`, default now).
- Money is `DECIMAL(14,2)`; percentage rates are `DECIMAL(5,2)`; no floating point.
- Status columns are PostgreSQL enums matching the values documented below.
- `NULL` = optional. `NOT NULL` = mandatory.
- `FK` = foreign key; `UK` = unique.
- Master-data deletion is a soft delete: records set `is_active = false` (and
  `deleted_at` where present), while financial history is never physically removed.

---

## 1. branches

| Column | Type | Key | Null | Default | Description |
| --- | --- | --- | --- | --- | --- |
| id | uuid | PK | no | gen_random_uuid() | Branch identifier |
| code | varchar(20) | UK | no | – | Short branch code (e.g. KLA) |
| name | varchar(120) |  | no | – | Branch name |
| physical_address | varchar(255) |  | yes | – | Office address |
| phone | varchar(30) |  | yes | – | Contact phone |
| email | varchar(120) |  | yes | – | Contact email |
| is_active | boolean |  | no | true | Active flag |
| created_at / updated_at | timestamptz |  | no | now() | Audit timestamps |

## 2. roles

| Column | Type | Key | Null | Default | Description |
| --- | --- | --- | --- | --- | --- |
| id | uuid | PK | no | gen_random_uuid() | Role identifier |
| code | varchar(40) | UK | no | – | Machine code (e.g. BROKER) |
| name | varchar(80) |  | no | – | Display name |
| description | varchar(255) |  | yes | – | Purpose |
| is_system | boolean |  | no | false | Protected system role |
| created_at / updated_at | timestamptz |  | no | now() | Audit timestamps |

## 3. permissions

| Column | Type | Key | Null | Default | Description |
| --- | --- | --- | --- | --- | --- |
| id | uuid | PK | no | gen_random_uuid() | Permission identifier |
| module | varchar(40) | UK* | no | – | Module code (e.g. clients) |
| action | varchar(20) | UK* | no | – | view/create/edit/approve/delete/report |
| description | varchar(255) |  | yes | – | Explanation |
| * Unique together `(module, action)` | | | | | |

## 4. role_permissions

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| role_id | uuid | PK, FK → roles.id | no | Role |
| permission_id | uuid | PK, FK → permissions.id | no | Permission |

Composite primary key `(role_id, permission_id)`; cascade on delete.

## 5. users

| Column | Type | Key | Null | Default | Description |
| --- | --- | --- | --- | --- | --- |
| id | uuid | PK | no | gen_random_uuid() | User identifier |
| employee_no | varchar(30) | UK | yes | – | HR/employee number |
| first_name | varchar(60) |  | no | – | First name |
| last_name | varchar(60) |  | no | – | Last name |
| email | varchar(150) | UK | no | – | Login email |
| phone | varchar(30) |  | yes | – | Phone |
| password_hash | varchar(255) |  | no | – | bcrypt hash |
| role_id | uuid | FK → roles.id | no | – | Assigned role |
| branch_id | uuid | FK → branches.id | yes | – | Home branch |
| is_active | boolean |  | no | true | Enabled flag |
| mfa_enabled | boolean |  | no | false | MFA enabled |
| mfa_secret | varchar(255) |  | yes | – | Encrypted TOTP secret (future) |
| must_change_password | boolean |  | no | false | Force password reset |
| failed_login_attempts | integer |  | no | 0 | Lockout counter |
| locked_until | timestamptz |  | yes | – | Lockout expiry |
| last_login_at | timestamptz |  | yes | – | Last successful login |
| created_by_id | uuid | FK → users.id | yes | – | Creator |
| created_at / updated_at | timestamptz |  | no | now() | Audit timestamps |

## 6. audit_logs

Append-only. No updates or deletes through the application.

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Log identifier |
| user_id | uuid | FK → users.id | yes | Actor (null for failed login) |
| user_email | varchar(150) |  | yes | Snapshot of actor email |
| action | varchar(40) |  | no | LOGIN, LOGOUT, CREATE, UPDATE, DELETE, APPROVE, UPLOAD, REPORT, EXPORT |
| module | varchar(40) |  | no | Module code |
| entity_type | varchar(60) |  | yes | Affected entity |
| entity_id | varchar(60) |  | yes | Affected record |
| description | varchar(500) |  | yes | Human summary |
| metadata | jsonb |  | yes | Before/after or extra data |
| ip_address | varchar(60) |  | yes | Client IP |
| user_agent | varchar(255) |  | yes | Client agent |
| created_at | timestamptz |  | no | Timestamp |

Indexes: `(created_at)`, `(user_id)`, `(module)`, `(entity_type, entity_id)`.

## 7. clients

| Column | Type | Key | Null | Default | Description |
| --- | --- | --- | --- | --- | --- |
| id | uuid | PK | no | gen_random_uuid() | Client identifier |
| client_type | enum client_type |  | no | INDIVIDUAL | INDIVIDUAL / CORPORATE |
| client_number | varchar(30) | UK | no | – | Business number `CLI-YYYY-####` |
| name | varchar(180) |  | no | – | Individual or company name |
| national_id | varchar(40) |  | yes | – | National ID (individual) |
| passport_no | varchar(40) |  | yes | – | Passport number |
| tin | varchar(40) |  | yes | – | Tax identification number |
| occupation | varchar(100) |  | yes | – | Occupation |
| date_of_birth | date |  | yes | – | DOB |
| gender | varchar(20) |  | yes | – | Gender |
| email | varchar(150) |  | yes | – | Email |
| phone | varchar(30) |  | no | – | Primary phone |
| alt_phone | varchar(30) |  | yes | – | Alternate phone |
| physical_address | varchar(255) |  | yes | – | Physical address |
| postal_address | varchar(255) |  | yes | – | Postal address |
| kyc_status | enum kyc_status |  | no | PENDING | PENDING/VERIFIED/REJECTED/EXPIRED |
| kyc_verified_at | timestamptz |  | yes | – | Verification timestamp |
| next_of_kin_name | varchar(120) |  | yes | – | Next of kin |
| next_of_kin_phone | varchar(30) |  | yes | – | Next of kin phone |
| next_of_kin_relationship | varchar(60) |  | yes | – | Relationship |
| registration_no | varchar(60) |  | yes | – | Company registration number |
| incorporation_date | date |  | yes | – | Incorporation date |
| business_sector | varchar(120) |  | yes | – | Sector |
| website | varchar(150) |  | yes | – | Website |
| notes | text |  | yes | – | Internal notes |
| branch_id | uuid | FK → branches.id | no | – | Owning branch |
| relationship_manager_id | uuid | FK → users.id | yes | – | Assigned broker |
| created_by_id | uuid | FK → users.id | yes | – | Creator |
| is_active | boolean |  | no | true | Active flag |
| deleted_at | timestamptz |  | yes | – | Soft delete |
| created_at / updated_at | timestamptz |  | no | now() | Audit timestamps |

Indexes: `name`, `phone`, `national_id`, `registration_no`, `client_number`.

## 8. client_contacts

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Contact identifier |
| client_id | uuid | FK → clients.id | no | Parent client (cascade) |
| full_name | varchar(120) |  | no | Contact name |
| job_title | varchar(100) |  | yes | Position |
| email | varchar(150) |  | yes | Email |
| phone | varchar(30) |  | yes | Phone |
| is_primary | boolean |  | no | Primary contact flag |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 9. client_directors

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Director identifier |
| client_id | uuid | FK → clients.id | no | Parent client (cascade) |
| full_name | varchar(120) |  | no | Director name |
| national_id | varchar(40) |  | yes | ID number |
| email | varchar(150) |  | yes | Email |
| phone | varchar(30) |  | yes | Phone |
| ownership_percentage | decimal(5,2) |  | yes | Shareholding % |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 10. insurers

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Insurer identifier |
| code | varchar(20) | UK | no | Short code |
| name | varchar(150) |  | no | Company name |
| email | varchar(150) |  | yes | Email |
| phone | varchar(30) |  | yes | Phone |
| physical_address | varchar(255) |  | yes | Address |
| website | varchar(150) |  | yes | Website |
| payment_instructions | text |  | yes | Bank/payment instructions |
| notes | text |  | yes | Notes |
| is_active | boolean |  | no | Active flag |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 11. insurer_contacts

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Contact identifier |
| insurer_id | uuid | FK → insurers.id | no | Parent insurer (cascade) |
| full_name | varchar(120) |  | no | Contact name |
| job_title | varchar(100) |  | yes | Position |
| email | varchar(150) |  | yes | Email |
| phone | varchar(30) |  | yes | Phone |
| is_primary | boolean |  | no | Primary contact |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 12. insurer_branches

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Branch identifier |
| insurer_id | uuid | FK → insurers.id | no | Parent insurer (cascade) |
| name | varchar(120) |  | no | Branch name |
| address | varchar(255) |  | yes | Address |
| phone | varchar(30) |  | yes | Phone |
| email | varchar(150) |  | yes | Email |
| is_active | boolean |  | no | Active flag |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 13. insurance_classes

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Class identifier |
| code | varchar(20) | UK | no | Code (MOTOR, FIRE…) |
| name | varchar(120) |  | no | Display name |
| category | enum class_category |  | no | GENERAL / LIFE |
| description | varchar(255) |  | yes | Description |
| is_active | boolean |  | no | Active flag |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 14. products

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Product identifier |
| code | varchar(30) | UK | no | Product code |
| name | varchar(150) |  | no | Product name |
| insurance_class_id | uuid | FK → insurance_classes.id | no | Class |
| insurer_id | uuid | FK → insurers.id | no | Offering insurer |
| underwriting_contact | varchar(150) |  | yes | Underwriting contact |
| required_documents | jsonb |  | yes | Array of document types |
| minimum_premium | decimal(14,2) |  | no | Minimum premium |
| commission_rate | decimal(5,2) |  | no | Default commission % |
| is_active | boolean |  | no | Active flag |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Unique `(insurer_id, name)`. Index `insurance_class_id`.

## 15. risks

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Risk identifier |
| risk_number | varchar(30) | UK | no | `RSK-YYYY-####` |
| client_id | uuid | FK → clients.id | no | Client |
| category | varchar(60) |  | no | MOTOR/FIRE/MARINE/… |
| location | varchar(255) |  | yes | Risk location |
| description | text |  | yes | Description |
| asset_details | jsonb |  | yes | Flexible asset data |
| previous_claims | text |  | yes | Claims history |
| status | enum risk_status |  | no | OPEN/UNDER_REVIEW/CLOSED |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 16. motor_details

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Motor detail identifier |
| risk_id | uuid | FK → risks.id | no | Parent risk (cascade) |
| registration_number | varchar(30) |  | no | Vehicle registration |
| chassis_number | varchar(60) |  | yes | Chassis/VIN |
| engine_number | varchar(60) |  | yes | Engine number |
| make | varchar(60) |  | no | Make |
| model | varchar(60) |  | yes | Model |
| year | integer |  | yes | Year of manufacture |
| vehicle_value | decimal(14,2) |  | no | Insured value |
| driver_name | varchar(120) |  | yes | Primary driver |
| driver_license_no | varchar(50) |  | yes | Driver licence |
| usage | varchar(60) |  | yes | Private/commercial |
| logbook_document_id | uuid | FK → documents.id | yes | Logbook upload |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Index `registration_number`.

## 17. quotations

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Quotation identifier |
| quotation_number | varchar(30) | UK | no | `QT-YYYY-####` |
| client_id | uuid | FK → clients.id | no | Client |
| product_id | uuid | FK → products.id | no | Product |
| risk_id | uuid | FK → risks.id | yes | Risk |
| broker_id | uuid | FK → users.id | no | Broker |
| branch_id | uuid | FK → branches.id | no | Branch |
| sum_insured | decimal(14,2) |  | no | Sum insured |
| premium | decimal(14,2) |  | no | Base premium |
| taxes | decimal(14,2) |  | no | Taxes |
| total_premium | decimal(14,2) |  | no | Premium + taxes |
| valid_from | date |  | no | Validity start |
| valid_to | date |  | no | Validity end |
| status | enum quotation_status |  | no | DRAFT/SENT/QUOTES_RECEIVED/SELECTED/ACCEPTED/DECLINED/EXPIRED |
| selected_insurer_id | uuid | FK → insurers.id | yes | Selected insurer |
| notes | text |  | yes | Notes |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 18. insurer_quotes

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Response identifier |
| quotation_id | uuid | FK → quotations.id | no | Quotation (cascade) |
| insurer_id | uuid | FK → insurers.id | no | Responding insurer |
| premium | decimal(14,2) |  | no | Quoted premium |
| taxes | decimal(14,2) |  | no | Taxes |
| terms | text |  | yes | Conditions |
| status | enum quote_response_status |  | no | REQUESTED/RECEIVED/DECLINED |
| received_at | timestamptz |  | yes | When received |
| valid_until | date |  | yes | Insurer validity |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Unique `(quotation_id, insurer_id)`.

## 19. policies

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Policy identifier |
| policy_number | varchar(40) | UK | no | `POL-YYYY-####` |
| client_id | uuid | FK → clients.id | no | Client |
| product_id | uuid | FK → products.id | no | Product |
| insurer_id | uuid | FK → insurers.id | no | Insurer |
| quotation_id | uuid | FK → quotations.id, UK | yes | Source quotation |
| branch_id | uuid | FK → branches.id | no | Branch |
| broker_id | uuid | FK → users.id | yes | Broker |
| sum_insured | decimal(14,2) |  | no | Sum insured |
| premium | decimal(14,2) |  | no | Base premium |
| taxes | decimal(14,2) |  | no | Taxes |
| total_premium | decimal(14,2) |  | no | Total |
| start_date | date |  | no | Inception |
| end_date | date |  | no | Expiry |
| renewal_date | date |  | no | Renewal date |
| status | enum policy_status |  | no | PENDING/ACTIVE/EXPIRED/CANCELLED/LAPSED |
| payment_frequency | varchar(20) |  | yes | ANNUAL/QUARTERLY/MONTHLY |
| commission_rate | decimal(5,2) |  | no | Snapshot rate |
| commission_amount | decimal(14,2) |  | no | Snapshot amount |
| notes | text |  | yes | Notes |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 20. endorsements

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Endorsement identifier |
| endorsement_number | varchar(40) | UK | no | `END-YYYY-####` |
| policy_id | uuid | FK → policies.id | no | Policy (cascade) |
| type | enum endorsement_type |  | no | ADDITION/DELETION/AMENDMENT/CANCELLATION/REINSTATEMENT |
| description | text |  | no | Details |
| effective_date | date |  | no | Effective date |
| premium_adjustment | decimal(14,2) |  | no | Signed adjustment |
| status | enum endorsement_status |  | no | DRAFT/PENDING_APPROVAL/APPROVED/REJECTED |
| requested_by_id | uuid | FK → users.id | yes | Requester |
| approved_by_id | uuid | FK → users.id | yes | Approver |
| approved_at | timestamptz |  | yes | Decision time |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 21. premiums (instalment schedule)

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Instalment identifier |
| policy_id | uuid | FK → policies.id | no | Policy (cascade) |
| installment_no | integer |  | no | Sequence |
| amount_due | decimal(14,2) |  | no | Due amount |
| amount_paid | decimal(14,2) |  | no | Paid amount |
| due_date | date |  | no | Due date |
| paid_at | timestamptz |  | yes | Payment time |
| status | enum premium_status |  | no | UNPAID/PARTIAL/PAID/OVERDUE/WAIVED |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Unique `(policy_id, installment_no)`.

## 22. invoices

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Invoice identifier |
| invoice_number | varchar(40) | UK | no | `INV-YYYY-####` |
| client_id | uuid | FK → clients.id | no | Client |
| policy_id | uuid | FK → policies.id | yes | Policy |
| issue_date | date |  | no | Issue date |
| due_date | date |  | no | Due date |
| subtotal | decimal(14,2) |  | no | Premium |
| tax | decimal(14,2) |  | no | Tax |
| total | decimal(14,2) |  | no | Total |
| amount_paid | decimal(14,2) |  | no | Allocated payments |
| status | enum invoice_status |  | no | DRAFT/ISSUED/PARTIAL/PAID/OVERDUE/CANCELLED |
| notes | text |  | yes | Notes |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 23. payments (receipts)

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Payment identifier |
| receipt_number | varchar(40) | UK | no | `RCT-YYYY-####` |
| client_id | uuid | FK → clients.id | no | Payer |
| policy_id | uuid | FK → policies.id | yes | Policy |
| invoice_id | uuid | FK → invoices.id | yes | Invoice allocated |
| amount | decimal(14,2) |  | no | Amount |
| method | enum payment_method |  | no | CASH/CHEQUE/BANK_TRANSFER/MOBILE_MONEY/CARD/OTHER |
| reference | varchar(100) |  | yes | Bank/mobile reference |
| paid_at | timestamptz |  | no | Payment time |
| status | enum payment_status |  | no | PENDING/CONFIRMED/REVERSED |
| received_by_id | uuid | FK → users.id | yes | Cashier |
| notes | text |  | yes | Notes |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 24. credit_debit_notes

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Note identifier |
| note_number | varchar(40) | UK | no | `CRN-`/`DBN-YYYY-####` |
| note_type | enum note_type |  | no | CREDIT / DEBIT |
| client_id | uuid | FK → clients.id | no | Client |
| policy_id | uuid | FK → policies.id | yes | Policy |
| amount | decimal(14,2) |  | no | Amount |
| reason | varchar(255) |  | no | Reason |
| status | enum note_status |  | no | DRAFT/ISSUED/APPLIED/CANCELLED |
| issue_date | date |  | no | Issue date |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 25. commissions

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Commission identifier |
| policy_id | uuid | FK → policies.id | no | Policy |
| insurer_id | uuid | FK → insurers.id | no | Insurer |
| broker_id | uuid | FK → users.id | yes | Broker |
| rate | decimal(5,2) |  | no | Applied rate |
| amount | decimal(14,2) |  | no | Amount |
| status | enum commission_status |  | no | PENDING/EARNED/PAID/RECONCILED/CANCELLED |
| earned_at | timestamptz |  | yes | Earned time |
| paid_at | timestamptz |  | yes | Insurer payment time |
| notes | text |  | yes | Notes |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Index `(status, earned_at)` for ageing.

## 26. remittances

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Remittance identifier |
| remittance_number | varchar(40) | UK | no | `REM-YYYY-####` |
| insurer_id | uuid | FK → insurers.id | no | Insurer |
| branch_id | uuid | FK → branches.id | yes | Branch |
| period_from | date |  | no | Period start |
| period_to | date |  | no | Period end |
| gross_premium | decimal(14,2) |  | no | Collected premium |
| commission_retained | decimal(14,2) |  | no | Commission retained |
| taxes | decimal(14,2) |  | no | Taxes |
| net_amount | decimal(14,2) |  | no | Payable to insurer |
| status | enum remittance_status |  | no | DRAFT/PENDING/PAID/RECONCILED |
| paid_at | timestamptz |  | yes | Payment time |
| reference | varchar(100) |  | yes | Bank reference |
| notes | text |  | yes | Notes |
| created_by_id | uuid | FK → users.id | yes | Creator |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 27. claims

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Claim identifier |
| claim_number | varchar(40) | UK | no | `CLM-YYYY-####` |
| policy_id | uuid | FK → policies.id | no | Policy |
| client_id | uuid | FK → clients.id | no | Client |
| date_of_loss | date |  | no | Loss date |
| reported_at | timestamptz |  | no | Notification time |
| cause | varchar(150) |  | no | Cause |
| description | text |  | yes | Details |
| surveyor | varchar(150) |  | yes | Surveyor |
| reserve_amount | decimal(14,2) |  | no | Reserve |
| paid_amount | decimal(14,2) |  | no | Paid |
| recovered_amount | decimal(14,2) |  | no | Recovered |
| status | enum claim_status |  | no | NOTIFIED/UNDER_REVIEW/RESERVED/APPROVED/PAID/SETTLED/REJECTED/CLOSED |
| settled_at | timestamptz |  | yes | Settlement time |
| notes | text |  | yes | Notes |
| handled_by_id | uuid | FK → users.id | yes | Claims officer |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 28. renewals

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Renewal identifier |
| policy_id | uuid | FK → policies.id | no | Policy (cascade) |
| due_date | date |  | no | Renewal due date |
| stage_days | integer |  | no | 90/60/30/14/7 reminder stage |
| status | enum renewal_status |  | no | UPCOMING/DUE/QUOTED/WON/LOST/LAPSED |
| renewal_quotation_id | uuid | FK → quotations.id | yes | Renewal quote |
| handled_by_id | uuid | FK → users.id | yes | Owner |
| won_at | timestamptz |  | yes | Won time |
| lost_at | timestamptz |  | yes | Lost time |
| lost_reason | varchar(255) |  | yes | Reason |
| notes | text |  | yes | Notes |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Unique `(policy_id, due_date)`.

## 29. documents

Polymorphic attachment store; files are written to the configured upload volume and
metadata is indexed here. Versioning uses `(entity_type, entity_id, name, version)`.

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Document identifier |
| entity_type | varchar(40) |  | no | CLIENT/RISK/POLICY/CLAIM/QUOTATION/INVOICE/… |
| entity_id | uuid |  | no | Related record |
| name | varchar(180) |  | no | Display file name |
| category | varchar(60) |  | yes | PROPOSAL/POLICY/INVOICE/RECEIPT/CLAIM/PHOTO/REPORT/OTHER |
| file_path | varchar(255) |  | no | Stored path |
| mime_type | varchar(100) |  | yes | MIME type |
| size | integer |  | yes | Bytes |
| version | integer |  | no | Version number |
| is_current | boolean |  | no | Current version |
| uploaded_by_id | uuid | FK → users.id | yes | Uploader |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

Index `(entity_type, entity_id)`.

## 30. communications

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Communication identifier |
| client_id | uuid | FK → clients.id | yes | Client |
| channel | enum comm_channel |  | no | EMAIL/SMS/PHONE/MEETING/LETTER/PORTAL |
| subject | varchar(180) |  | yes | Subject |
| message | text |  | no | Body |
| related_entity_type | varchar(40) |  | yes | Related record type |
| related_entity_id | uuid |  | yes | Related record |
| sent_at | timestamptz |  | yes | Sent time |
| status | varchar(20) |  | no | QUEUED/SENT/FAILED/LOGGED |
| sent_by_id | uuid | FK → users.id | yes | Staff member |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 31. tasks

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Task identifier |
| title | varchar(180) |  | no | Title |
| description | text |  | yes | Details |
| assigned_to_id | uuid | FK → users.id | no | Assignee |
| related_entity_type | varchar(40) |  | yes | Related record type |
| related_entity_id | uuid |  | yes | Related record |
| due_date | date |  | yes | Due date |
| priority | enum priority |  | no | LOW/MEDIUM/HIGH/URGENT |
| status | enum task_status |  | no | TODO/IN_PROGRESS/DONE/CANCELLED |
| created_by_id | uuid | FK → users.id | yes | Creator |
| completed_at | timestamptz |  | yes | Completion time |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 32. approvals

| Column | Type | Key | Null | Description |
| --- | --- | --- | --- | --- |
| id | uuid | PK | no | Approval identifier |
| type | enum approval_type |  | no | QUOTATION/COMMISSION_OVERRIDE/ENDORSEMENT/REFUND/CREDIT_TERMS/CLAIM_SETTLEMENT |
| entity_type | varchar(40) |  | no | Entity under approval |
| entity_id | uuid |  | no | Entity identifier |
| amount | decimal(14,2) |  | yes | Amount under consideration |
| requested_by_id | uuid | FK → users.id | no | Requester |
| approver_id | uuid | FK → users.id | yes | Decision maker |
| status | enum approval_status |  | no | PENDING/APPROVED/REJECTED/CANCELLED |
| comments | text |  | yes | Decision comments |
| requested_at | timestamptz |  | no | Request time |
| decided_at | timestamptz |  | yes | Decision time |
| created_at / updated_at | timestamptz |  | no | Audit timestamps |

## 9. Enum reference

| Enum | Values |
| --- | --- |
| client_type | INDIVIDUAL, CORPORATE |
| kyc_status | PENDING, VERIFIED, REJECTED, EXPIRED |
| class_category | GENERAL, LIFE |
| risk_status | OPEN, UNDER_REVIEW, CLOSED |
| quotation_status | DRAFT, SENT, QUOTES_RECEIVED, SELECTED, ACCEPTED, DECLINED, EXPIRED |
| quote_response_status | REQUESTED, RECEIVED, DECLINED |
| policy_status | PENDING, ACTIVE, EXPIRED, CANCELLED, LAPSED |
| endorsement_type | ADDITION, DELETION, AMENDMENT, CANCELLATION, REINSTATEMENT |
| endorsement_status | DRAFT, PENDING_APPROVAL, APPROVED, REJECTED |
| premium_status | UNPAID, PARTIAL, PAID, OVERDUE, WAIVED |
| invoice_status | DRAFT, ISSUED, PARTIAL, PAID, OVERDUE, CANCELLED |
| payment_method | CASH, CHEQUE, BANK_TRANSFER, MOBILE_MONEY, CARD, OTHER |
| payment_status | PENDING, CONFIRMED, REVERSED |
| note_type | CREDIT, DEBIT |
| note_status | DRAFT, ISSUED, APPLIED, CANCELLED |
| commission_status | PENDING, EARNED, PAID, RECONCILED, CANCELLED |
| remittance_status | DRAFT, PENDING, PAID, RECONCILED |
| claim_status | NOTIFIED, UNDER_REVIEW, RESERVED, APPROVED, PAID, SETTLED, REJECTED, CLOSED |
| renewal_status | UPCOMING, DUE, QUOTED, WON, LOST, LAPSED |
| comm_channel | EMAIL, SMS, PHONE, MEETING, LETTER, PORTAL |
| priority | LOW, MEDIUM, HIGH, URGENT |
| task_status | TODO, IN_PROGRESS, DONE, CANCELLED |
| approval_type | QUOTATION, COMMISSION_OVERRIDE, ENDORSEMENT, REFUND, CREDIT_TERMS, CLAIM_SETTLEMENT |
| approval_status | PENDING, APPROVED, REJECTED, CANCELLED |

## 10. Numbering sequences

| Entity | Format | Example |
| --- | --- | --- |
| Client | CLI-{YYYY}-{seq:4} | CLI-2026-0001 |
| Risk | RSK-{YYYY}-{seq:4} | RSK-2026-0001 |
| Quotation | QT-{YYYY}-{seq:4} | QT-2026-0001 |
| Policy | POL-{YYYY}-{seq:4} | POL-2026-0001 |
| Endorsement | END-{YYYY}-{seq:4} | END-2026-0001 |
| Invoice | INV-{YYYY}-{seq:4} | INV-2026-0001 |
| Receipt | RCT-{YYYY}-{seq:4} | RCT-2026-0001 |
| Credit/Debit note | CRN-/DBN-{YYYY}-{seq:4} | CRN-2026-0001 |
| Remittance | REM-{YYYY}-{seq:4} | REM-2026-0001 |
| Claim | CLM-{YYYY}-{seq:4} | CLM-2026-0001 |

Sequences are generated transactionally from the maximum existing value per year to
avoid duplicates under concurrent use.
<!-- 2026-11-11T15:06:08Z client dict -->
