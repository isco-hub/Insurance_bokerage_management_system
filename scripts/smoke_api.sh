#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:4000/api}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@ibms.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Password123!}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1" >&2; exit 1; }

json() {
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))" "$1" "$2"
}

printf 'API smoke test against %s\n\n' "$API_URL"

status="$(curl -sS -o "$TMP_DIR/health.json" -w '%{http_code}' "$API_URL/health/")"
[[ "$status" == "200" ]] || fail "health returned HTTP $status"
[[ "$(json "$TMP_DIR/health.json" "d['status']")" == "ok" ]] || fail "health status is not ok"
pass "health endpoint"

login_status="$(curl -sS -o "$TMP_DIR/login.json" -w '%{http_code}' \
  -X POST "$API_URL/auth/login/" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")"
[[ "$login_status" == "200" ]] || fail "login returned HTTP $login_status"
TOKEN="$(json "$TMP_DIR/login.json" "d['data']['token']")"
[[ -n "$TOKEN" ]] || fail "login response did not include a token"
pass "admin login"

auth_get() {
  local path="$1" name="$2" check="$3"
  local code
  code="$(curl -sS -o "$TMP_DIR/response.json" -w '%{http_code}' \
    -H "Authorization: Bearer $TOKEN" "$API_URL$path")"
  [[ "$code" == "200" ]] || fail "$name returned HTTP $code"
  [[ "$(json "$TMP_DIR/response.json" "$check")" != "" ]] || fail "$name check failed: $check"
  pass "$name"
}

auth_get "/auth/me/" "current user" "d['data']['email']"
auth_get "/dashboard/" "dashboard" "d['data']['kpis']['active_clients']"
auth_get "/clients/?page=1&pageSize=5" "clients list" "len(d['data'])"
CLIENT_ID="$(json "$TMP_DIR/response.json" "d['data'][0]['id']")"
auth_get "/clients/$CLIENT_ID/" "client detail" "d['data']['name']"
auth_get "/policies/?page=1&pageSize=5" "policies list" "len(d['data'])"
auth_get "/quotations/?page=1&pageSize=5" "quotations list" "len(d['data'])"
auth_get "/payments/?page=1&pageSize=5" "payments list" "len(d['data'])"
auth_get "/claims/?page=1&pageSize=5" "claims list" "len(d['data'])"
auth_get "/tasks/?page=1&pageSize=5" "tasks list" "len(d['data'])"
auth_get "/approvals/?page=1&pageSize=5" "approvals list" "len(d['data'])"
APPROVAL_ID="$(json "$TMP_DIR/response.json" "d['data'][0]['id']")"
auth_get "/approvals/$APPROVAL_ID/review/" "approval review context" "d['data']['approval']['id']"
auth_get "/reports/premium-production/" "premium production report" "len(d['data']['rows'])"
auth_get "/reports/claims/" "claims report" "len(d['data']['rows'])"
auth_get "/reports/commission-ageing/" "commission ageing report" "len(d['data']['buckets'])"
auth_get "/reports/commission-statement/" "commission statement report" "len(d['data']['by_insurer'])"
auth_get "/reports/remittance-reconciliation/" "remittance reconciliation report" "len(d['data']['rows'])"
auth_get "/reports/debtors-ageing/" "debtors ageing report" "len(d['data']['buckets'])"
auth_get "/reports/quotation-conversion/" "quotation conversion report" "d['data']['summary']['total']"
auth_get "/reports/claim-analysis/" "claims analysis report" "len(d['data']['by_status'])"
auth_get "/reports/business-by-client/" "business by client report" "len(d['data']['rows'])"
auth_get "/reports/policy-register/" "policy register report" "len(d['data']['rows'])"
auth_get "/search/?q=POL" "global search" "sum(len(g['items']) for g in d['data']['groups'])"

export_status="$(curl -sS -D "$TMP_DIR/export.headers" -o "$TMP_DIR/export.csv" -w '%{http_code}'   -H "Authorization: Bearer $TOKEN" "$API_URL/reports/premium-production/export/")"
[[ "$export_status" == "200" ]] || fail "report export returned HTTP $export_status"
grep -qi '^Content-Type: text/csv' "$TMP_DIR/export.headers" || fail "report export is not CSV"
grep -q 'policy_number' "$TMP_DIR/export.csv" || fail "report export CSV header is missing"
pass "report CSV export"

validation_status="$(curl -sS -o "$TMP_DIR/invalid.json" -w '%{http_code}' \
  -X POST "$API_URL/auth/login/" \
  -H 'Content-Type: application/json' \
  -d '{"email":"nobody@example.com","password":"wrong"}')"
[[ "$validation_status" == "401" ]] || fail "invalid login returned HTTP $validation_status (expected 401)"
pass "invalid login rejected"

echo
printf 'All API smoke checks passed.\n'
