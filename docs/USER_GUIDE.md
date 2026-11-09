# User Guide

This guide is for day-to-day users of the Insurance Brokerage Management System
(IBMS). It covers navigation, common list behaviour and the main business workflows.
Menu items are shown only when your role has the matching permission, so a finance
user, broker and administrator may see different menus. All monetary values are in
Ugandan shillings (`UGX`), displayed as `USh`.

## 1. Signing in

Open http://localhost:8080 to see the public landing page, then choose **Sign in**
and enter your work email and password. The seeded demo accounts all use
`Password123!` unless the deployment changed `SEED_PASSWORD`.

| Role | Email |
| --- | --- |
| System Administrator | admin@ibms.local |
| Managing Director | md@ibms.local |
| Operations Manager | ops@ibms.local |
| Branch Manager | branch@ibms.local |
| Broker | broker@ibms.local |
| Underwriting Officer | underwriting@ibms.local |
| Claims Officer | claims@ibms.local |
| Finance Officer | finance@ibms.local |
| Customer Service Officer | service@ibms.local |
| Auditor | auditor@ibms.local |

Five failed sign-in attempts lock the account for 15 minutes by default. Ask an
administrator to unlock it from **Users** if needed. Users in branch-scoped roles
(`BRANCH`, `BROKER`, `SERVICE`) see records for their own branch only.

Open **Account settings** from the profile menu to review your profile and change
your password. If an administrator requires a password reset, the app redirects you
to the account page until the password has been changed.

## 2. Dashboard and navigation

The dashboard shows eight live indicators covering clients, policies, premium
collection, claims, renewals and quotations. Use the sidebar groups:

- **Overview** — Dashboard and Reports.
- **Customer Relationship** — Clients, Client Contacts, Client Directors, Insurers,
  Insurer Contacts, Insurer Branches, Products and Insurance Classes.
- **Brokerage Operations** — Risks, Motor Details, Quotations, Insurer Quotes,
  Policies, Endorsements and Renewals.
- **Finance** — Premiums, Invoices, Payments, Credit / Debit Notes, Commissions and
  Remittances.
- **Claims** — Claims register and settlement.
- **Workspace** — Tasks, Approvals, Documents and Communications.
- **Administration** — Users, Roles & Permissions, Branches and Audit Trail.

The global search box in the header finds clients, policies, quotations, claims and
insurers. Press Enter or choose **Search** to see grouped results.

## 3. Common list screens

Every module uses the same pattern:

1. Use the search box to find records by the fields shown in the placeholder.
2. Use the filter controls to narrow by status, type, branch, insurer or similar.
3. Use the column sort arrows where available.
4. Use **New** / **Create** to add a record; required fields are marked with `*`.
5. Use the row **Edit** action to update a record.
6. Use **Delete** to remove a record. Master data such as clients, insurers,
   products and branches is deactivated rather than physically deleted. Branches,
   insurers and products remain visible as inactive and can be reactivated by
   editing **Active**; clients marked deleted are hidden from normal lists.
7. Use the eye icon in the Actions column to open the record detail page, where
   linked documents and communications are shown.
8. Move between pages with the pagination controls. The default page size is 20.
   Lists refresh automatically every 30 seconds; use **Refresh** for an immediate
   update.

Read-only modules (Audit Trail) do not show create, edit or delete actions. Fields
that are greyed out in a form are calculated by the system and cannot be edited.

## 4. Customer Relationship

### Clients

Create individual or corporate clients with contact details, KYC status, branch and
relationship manager. Corporate clients can also have directors and registration
details. Client numbers are generated automatically. Use the **Policies** column to
see how many policies the client holds.

### Client Contacts and Directors

These pages hold the people associated with a client. A contact can be marked
**Primary**. Directors are mainly used for corporate clients, including the
percentage owned. Both records are linked to the client through a dropdown.

### Insurers, Contacts and Branches

Maintain insurance partner details, their underwriting/claims contacts and their
branch offices. Insurer and product information is used when creating quotations
and policies. Inactive insurers remain visible but should not be selected for new
business.

### Products and Insurance Classes

Products belong to an insurance class and an insurer. They define the minimum
premium, commission rate, underwriting contact and required documents. Classes group
products for reporting. Keep commission rates up to date because they drive
commission records and reports.

## 5. Brokerage Operations

### Risks

A risk records what is being insured: client, category, location, description,
asset details and previous claims. The risk number is generated automatically.
Motor risks can have one or more motor detail records attached.

### Motor Details

Attach vehicle registration, chassis and engine numbers, make/model/year, vehicle
value, driver details and the logbook document to a risk. The risk dropdown shows
generated risk numbers.

### Quotations

1. Create a quotation for a client, product and risk. Enter the sum insured,
   premium, taxes and validity dates.
2. Create **Insurer Quotes** for each insurer approached, recording premium, taxes,
   terms and status. Mark a response as **Received** when it arrives.
3. On the quotation row choose **Select insurer** and pick the received insurer
   quote. The quotation becomes **Selected**.
4. Choose **Accept → policy**. Enter the policy start/end dates, payment frequency
   and notes. The system creates the policy, premium schedule and commission.

If the total premium is at or above `HIGH_VALUE_QUOTE_THRESHOLD` (default 50,000), an
approval request is created and acceptance is blocked until an authorised user
approves it in **Approvals**. Quotations past their validity date cannot be accepted.

### Policies

Policies are normally created by accepting a quotation. The register shows insurer,
product, sum insured, premium, dates, status and outstanding premium. Use the row
actions to view or edit the policy. Policy status values are Pending, Active,
Expired, Cancelled and Lapsed. **Cancel policy** requires an effective date and
reason; open renewals lapse and pending commissions are cancelled automatically.

### Endorsements

Create an endorsement when a policy changes (addition, deletion, amendment,
cancellation or reinstatement). Enter the effective date, description and premium
adjustment. An approver other than the requester must approve or reject it. An
approved adjustment automatically creates a credit or debit note.

### Renewals

Renewal records track policies approaching expiry. Update the stage/status and use
the **Outcome** action to mark a renewal **Won**, **Lost** or **Lapsed**. A lost
renewal should include a reason.

The scheduler sends client reminders at the 90, 60, 30, 14 and 7-day stages and
prepares a draft renewal quotation automatically when a renewal is within 60 days
and no quotation is linked. Overdue premium instalments are marked **Overdue** and
collection reminders are sent every seven days. If email or SMS delivery is not
possible, an internal follow-up task is assigned to the broker or relationship
manager instead.

## 6. Finance

### Premiums

Premiums are generated from policies as installments. `amount_due`, `amount_paid`
and `balance` show the collection position. Statuses are Unpaid, Partial, Paid,
Overdue and Waived. Payments update these values automatically.

### Invoices

Create invoices against a client and policy. Invoice numbers are generated. Enter
the subtotal and tax; the total, amount paid and balance are maintained by the
system. Statuses are Draft, Issued, Partial, Paid, Overdue and Cancelled.

### Payments

Record the client, amount, method, reference and date. Receipt numbers are generated
and the payment is allocated to outstanding premiums and invoices by the allocation
service. Bank transfer, cheque, mobile money, card, cash and other methods are
supported. Use **Refund** on a confirmed payment to record a full or partial refund;
invoice and premium balances are reversed and the payment becomes **Reversed** when
fully refunded.

### Credit / Debit Notes

Use a credit note to reduce a client balance and a debit note to increase it. Notes
are linked to a client and optionally a policy, and carry a reason and issue date.

### Commissions

Commissions are generated from policy commission rates. Finance can mark a commission
**Paid** and an authorised user can **Reconcile** it. The status flow is Pending,
Earned, Paid, Reconciled or Cancelled.

### Remittances

A remittance advice summarises premium due to an insurer for a period. Create one
manually or use **Generate advice** by insurer and date range. The system calculates
gross premium, commission retained, taxes and net amount. Mark it paid with a bank
reference, then reconcile it. Reconciliation requires the matched amount to equal
the remittance net amount exactly.

## 7. Claims

1. Create a claim against a policy and client with the loss date, cause, description
   and reserve amount.
2. Update the claim status as it progresses: Notified, Under review, Reserved,
   Approved, Paid, Settled, Rejected or Closed.
3. When the claim is ready, choose **Settle claim**, enter the paid amount, any
   recovery and notes. The claim becomes **Settled** and records the settlement time.

Claims are branch-scoped for branch users. Settlement requires claims approval
permission.

## 8. Workspace

- **Tasks** — create follow-ups with owner, due date, priority and linked record. Use
  **Complete** when done.
- **Approvals** — open a request to review the approval beside the linked quotation,
  policy, claim or finance record. Approve or reject with comments. You cannot
  approve your own request.
- **Documents** — upload files against a client, policy, claim, quotation or insurer.
  File links open the stored document; a new upload with the same name becomes the
  current version and historical versions remain listed.
- **Communications** — log emails, calls, SMS, meetings, letters and portal messages
  linked to clients and records. Use **Send** for email or SMS; email uses the client
  address and SMS requires a configured gateway and client phone number.

## 9. Reports

Open **Reports** and choose one of the twenty-one reports:

Premium production, Business mix, Commission register, Commission ageing, Commission
statement, Remittance reconciliation, Debtors ageing, Quotation conversion, Claims
analysis, Business by client, Policy register, Premium collections, Outstanding
premiums, Outstanding debtors, Claims register, Renewals, Staff performance,
Expiring policies, Lost business, Accounting export and Audit summary.

Set the From/To date range, then review the summary cards, detailed rows and any
grouped sections. Use **Export CSV** to download the selected report or **Reset
dates** to clear the range. Report data is restricted by your permissions and, for
branch-scoped roles, by branch.

## 10. Administration

- **Users** — create users, assign a role and branch, activate/deactivate access and
  use **Unlock** to clear a failed-login lockout. Leave the password blank when
  editing to keep the existing password.
- **Roles & Permissions** — assign module/action permissions to roles. The ADMIN role
  bypasses the permission matrix.
- **Branches** — maintain branch offices. Branch users are tied to one branch.
- **Audit Trail** — read-only log of logins, failures, creates, updates, deletes,
  approvals and other actions. Filter by action, module or user.

## 11. Common problems

| Problem | What to do |
| --- | --- |
| A menu item is missing | Your role does not have the module view permission; ask an administrator |
| You cannot see another branch's records | Branch-scoped roles only see their own branch |
| A record cannot be deleted | Master data is deactivated; edit it and set Active back on to restore it |
| Quotation acceptance is blocked | It needs management approval or the validity date has passed |
| Payment does not reduce a balance | Confirm the payment is linked to the correct client/policy and is Confirmed |
| Communication shows Failed | Check the client email/phone and the SMTP or SMS gateway configuration |
| Remittance cannot reconcile | The matched amount must exactly equal the remittance net amount |
| Login is locked | Wait for the lockout period or ask an administrator to reset it |
