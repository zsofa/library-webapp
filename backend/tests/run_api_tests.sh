#!/usr/bin/env bash
# Library API integration tests (JWT) with colors, timing, and per-section summaries.
# Usage: ./tests/run_api_tests.sh [BASE_URL]
# Deps: curl, jq

set -u -o pipefail

# ---------- Colors ----------
if [[ -t 2 ]]; then
  RED="$(printf '\033[31m')"
  GREEN="$(printf '\033[32m')"
  YELLOW="$(printf '\033[33m')"
  BLUE="$(printf '\033[34m')"
  MAGENTA="$(printf '\033[35m')"
  BOLD="$(printf '\033[1m')"
  DIM="$(printf '\033[2m')"
  RESET="$(printf '\033[0m')"
else
  RED=""; GREEN=""; YELLOW=""; BLUE=""; MAGENTA=""; BOLD=""; DIM=""; RESET=""
fi

BASE_URL="${1:-http://localhost:5000/api}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="api_test_results_${TS}.txt"

TOTAL=0
PASSED=0
FAILED=0

# Section counters
declare -A SEC_TOTAL SEC_PASS SEC_FAIL

sec_start() {
  local s="$1"
  SEC_TOTAL["$s"]=0
  SEC_PASS["$s"]=0
  SEC_FAIL["$s"]=0
}

sec_count() {
  local s="$1" ok="$2"
  SEC_TOTAL["$s"]=$((SEC_TOTAL["$s"]+1))
  if [[ "$ok" == "1" ]]; then
    SEC_PASS["$s"]=$((SEC_PASS["$s"]+1))
  else
    SEC_FAIL["$s"]=$((SEC_FAIL["$s"]+1))
  fi
}

# ---------- Logging ----------
log() { echo -e "$@" | tee -a "$OUT_FILE" >&2; }
section_header() { log "\n${BOLD}==================== $* ====================${RESET}"; }
subheader() { log "${MAGENTA}-- $* --${RESET}"; }
info() { log "${YELLOW}$@${RESET}"; }
pass() { log "${GREEN}PASS${RESET} $@"; }
fail() { log "${RED}FAIL${RESET} $@"; }
timing() { log "${DIM}(${1} ms)${RESET}"; }

echo "Running API tests against ${BASE_URL}" | tee "$OUT_FILE"
echo "Timestamp: $TS" | tee -a "$OUT_FILE"
echo "Logging to $OUT_FILE" | tee -a "$OUT_FILE"
echo "" | tee -a "$OUT_FILE"

# ---------- HTTP helper ----------
api_raw() {
  local method="$1"; shift
  local path="$1"; shift
  local token="${1:-}"; shift || true
  local data="${1:-}"; shift || true

  local url="${BASE_URL}${path}"
  local auth_header=()
  local data_args=()

  [[ -n "$token" ]] && auth_header=(-H "Authorization: Bearer $token")
  [[ -n "$data"  ]] && data_args=(-H "Content-Type: application/json" -d "$data")

  # measure time (ms)
  local start end elapsed
  start="$(date +%s%3N)"
  local resp
  resp="$(curl -sS -X "$method" "$url" "${auth_header[@]}" "${data_args[@]}" -w "\n%{http_code}")"
  end="$(date +%s%3N)"
  elapsed=$((end - start))
  echo "$resp"
  echo "$elapsed"  # extra line at end for timing
}

# expect NAME SECTION METHOD PATH TOKEN BODY_JSON EXPECT_STATUS [JQ_FILTER EXPECT_VALUE]
expect() {
  local name="$1"; shift
  local section="$1"; shift
  local method="$1"; shift
  local path="$1"; shift
  local token="$1"; shift
  local data="$1"; shift
  local expect_status="$1"; shift
  local jq_filter="${1:-}"; shift || true
  local expect_value="${1:-}"; shift || true

  TOTAL=$((TOTAL+1))
  SEC_TOTAL["$section"]=$((SEC_TOTAL["$section"]+1))

  subheader "TEST: $name"
  log "REQ: ${method} ${path}"
  [[ -n "$data" ]] && log "BODY: $data"

  local resp status body elapsed
  resp="$(api_raw "$method" "$path" "$token" "$data")"
  status="$(echo "$resp" | tail -n2 | head -n1)"
  elapsed="$(echo "$resp" | tail -n1)"
  body="$(echo "$resp" | sed '$d' | sed '$d')"

  log "STATUS: $status"
  log "BODY: $body"
  timing "$elapsed"

  local ok=1
  if [[ "$status" != "$expect_status" ]]; then
    ok=0
    log "Expected status: $expect_status, got: $status"
  fi
  if [[ "$ok" == "1" && -n "$jq_filter" ]]; then
    local actual
    if ! actual="$(echo "$body" | jq -r "$jq_filter" 2>/dev/null)"; then
      ok=0
      log "jq parse failed for filter: $jq_filter"
    elif [[ "$actual" != "$expect_value" ]]; then
      ok=0
      log "Expected jq '$jq_filter' == '$expect_value', got '$actual'"
    fi
  fi

  # meta.request_id sanity for error responses
  if [[ "$ok" == "1" && "$expect_status" =~ ^4|5 ]]; then
    local rid
    rid="$(echo "$body" | jq -r '.meta.request_id // empty')"
    if [[ -z "$rid" ]]; then
      ok=0
      log "Expected meta.request_id for error response but not found."
    fi
  fi

  if [[ "$ok" == "1" ]]; then
    PASSED=$((PASSED+1)); SEC_PASS["$section"]=$((SEC_PASS["$section"]+1)); pass "$name"
  else
    FAILED=$((FAILED+1)); SEC_FAIL["$section"]=$((SEC_FAIL["$section"]+1)); fail "$name"
  fi

  # Return body (JSON) to caller
  echo "$body"
}

# Initialize sections
for S in "health" "auth" "ratelimit" "users" "books" "loans" "reservations" "admin" "logout"; do
  sec_start "$S"
done

############################################################
# Section: Health / OpenAPI / 404
############################################################
section_header "Core / Health"
expect "Health check" "health" "GET" "/health" "" "" "200" '.status' 'ok' >/dev/null

# OpenAPI optional — COUNT IT via expect
OA_RESP="$(api_raw "GET" "/openapi.yaml" "" "")"
OA_STATUS="$(echo "$OA_RESP" | tail -n2 | head -n1)"
if [[ "$OA_STATUS" == "200" ]]; then
  # Count as a test
  expect "OpenAPI served" "health" "GET" "/openapi.yaml" "" "" "200" >/dev/null
else
  expect "OpenAPI 404 structured" "health" "GET" "/openapi.yaml" "" "" "404" '.error' 'not_found' >/dev/null
fi

expect "Global 404 handler" "health" "GET" "/no_such/endpoint" "" "" "404" '.error' 'not_found' >/dev/null

############################################################
# Section: Auth
############################################################
section_header "Auth"
TEST_EMAIL="autotest_${TS}@example.com"

expect "Register missing fields" "auth" "POST" "/register" "" '{}' "400" '.error' 'missing_fields' >/dev/null
expect "Register invalid DOB" "auth" "POST" "/register" "" \
  '{"email":"x@y.z","password":"pw","name":"X","address":"Addr","date_of_birth":"12-31-1999"}' \
  "400" '.error' 'invalid_date_of_birth' >/dev/null
expect "Register OK" "auth" "POST" "/register" "" \
  "{\"email\":\"$TEST_EMAIL\",\"password\":\"secret123\",\"name\":\"API User\",\"address\":\"Somewhere\",\"date_of_birth\":\"2000-01-01\"}" \
  "201" '.email' "$TEST_EMAIL" >/dev/null
expect "Register duplicate" "auth" "POST" "/register" "" \
  "{\"email\":\"$TEST_EMAIL\",\"password\":\"secret123\",\"name\":\"Dup\",\"address\":\"Somewhere\",\"date_of_birth\":\"2000-01-01\"}" \
  "409" '.error' 'email_exists' >/dev/null

# MISSING EARLIER: add back login missing credentials
expect "Login missing credentials" "auth" "POST" "/login" "" '{}' "400" '.error' 'missing_credentials' >/dev/null

LOGIN_BODY="$(expect "Login OK" 'auth' 'POST' '/login' '' "{\"email\":\"$TEST_EMAIL\",\"password\":\"secret123\"}" '200')"
TEST_ACCESS_TOKEN="$(echo "$LOGIN_BODY" | jq -r '.access_token')"
TEST_REFRESH_TOKEN="$(echo "$LOGIN_BODY" | jq -r '.refresh_token // empty')"
TEST_USER_ID="$(echo "$LOGIN_BODY" | jq -r '.user.user_id')"

ADMIN_LOGIN_BODY="$(expect "Admin login" 'auth' 'POST' '/login' '' '{"email":"admin@library.hu","password":"admin123456.!"}' '200')"
ADMIN_ACCESS_TOKEN="$(echo "$ADMIN_LOGIN_BODY" | jq -r '.access_token')"

expect "/me invalid token" "auth" "GET" "/me" "ey.invalid.token" "" "401" >/dev/null
expect "/me OK" "auth" "GET" "/me" "$TEST_ACCESS_TOKEN" "" "200" '.user_id|tostring' "$TEST_USER_ID" >/dev/null

if [[ -n "$TEST_REFRESH_TOKEN" && "$TEST_REFRESH_TOKEN" != "null" ]]; then
  expect "Refresh OK" "auth" "POST" "/token/refresh" "$TEST_REFRESH_TOKEN" "" "200" >/dev/null
else
  info "Refresh token not given – skipping refresh test."
fi

############################################################
# Section: Rate limit
############################################################
section_header "Auth Rate Limit"
ATTEMPTS="${LOGIN_RATE_LIMIT_ATTEMPTS:-5}"
RATE_A="rateA_${TS}@example.com"
RATE_B="rateB_${TS}@example.com"
PW="Secret123"

expect "RateA register" "ratelimit" "POST" "/register" "" "{\"email\":\"$RATE_A\",\"password\":\"$PW\",\"name\":\"RL\",\"address\":\"X\",\"date_of_birth\":\"1990-01-01\"}" "201" >/dev/null
expect "RateB register" "ratelimit" "POST" "/register" "" "{\"email\":\"$RATE_B\",\"password\":\"$PW\",\"name\":\"RL\",\"address\":\"X\",\"date_of_birth\":\"1990-01-01\"}" "201" >/dev/null

for i in $(seq 1 "$ATTEMPTS"); do
  expect "RateA fail $i" "ratelimit" "POST" "/login" "" "{\"email\":\"$RATE_A\",\"password\":\"WRONG_$i\"}" "401" '.error' 'invalid_credentials' >/dev/null
done
expect "RateA throttled" "ratelimit" "POST" "/login" "" "{\"email\":\"$RATE_A\",\"password\":\"WRONG_final\"}" "429" '.error' 'too_many_attempts' >/dev/null

for i in $(seq 1 $((ATTEMPTS-1))); do
  expect "RateB fail $i" "ratelimit" "POST" "/login" "" "{\"email\":\"$RATE_B\",\"password\":\"BAD_$i\"}" "401" '.error' 'invalid_credentials' >/dev/null
done
expect "RateB success resets counter" "ratelimit" "POST" "/login" "" "{\"email\":\"$RATE_B\",\"password\":\"$PW\"}" "200" >/dev/null
expect "RateB post-reset fail" "ratelimit" "POST" "/login" "" "{\"email\":\"$RATE_B\",\"password\":\"WRONG_after\"}" "401" '.error' 'invalid_credentials' >/dev/null

############################################################
# Section: Users
############################################################
section_header "Users"
expect "Get self" "users" "GET" "/users/$TEST_USER_ID" "$TEST_ACCESS_TOKEN" "" "200" '.user_id|tostring' "$TEST_USER_ID" >/dev/null
expect "Member cannot view other" "users" "GET" "/users/999999" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "Admin get non-existing" "users" "GET" "/users/999999" "$ADMIN_ACCESS_TOKEN" "" "404" '.error' 'user_not_found' >/dev/null
expect "Update no fields" "users" "PUT" "/users/$TEST_USER_ID" "$TEST_ACCESS_TOKEN" '{}' "400" '.error' 'no_fields_to_update' >/dev/null
expect "Update invalid DOB" "users" "PUT" "/users/$TEST_USER_ID" "$TEST_ACCESS_TOKEN" '{"date_of_birth":"31/12/1999"}' "400" '.error' 'invalid_date_of_birth' >/dev/null
expect "Update OK" "users" "PUT" "/users/$TEST_USER_ID" "$TEST_ACCESS_TOKEN" '{"name":"Updated","address":"New","date_of_birth":"1999-12-31"}' "200" '.name' 'Updated' >/dev/null
expect "Admin updates user" "users" "PUT" "/users/$TEST_USER_ID" "$ADMIN_ACCESS_TOKEN" '{"address":"Admin Addr"}' "200" '.address' 'Admin Addr' >/dev/null

############################################################
# Section: Books
############################################################
section_header "Books"
BOOKS_LIST="$(expect "List books" "books" "GET" "/books" "" "" "200")"
BOOK_ID="$(echo "$BOOKS_LIST" | jq 'if type=="array" and length>0 then (map(select(.available_items>0))[0].book_id // .[0].book_id) else 1 end')"
info "Picked BOOK_ID=$BOOK_ID"

expect "Search q=the" "books" "GET" "/books?q=the" "" "" "200" >/dev/null
expect "Filter category Sci-fi" "books" "GET" "/books?category=Sci-fi" "" "" "200" >/dev/null
expect "Book not found 404" "books" "GET" "/books/999999" "" "" "404" '.error' 'book_not_found' >/dev/null
expect "Get valid book" "books" "GET" "/books/$BOOK_ID" "" "" "200" '.book_id' "$BOOK_ID" >/dev/null

############################################################
# Section: Loans
############################################################
section_header "Loans"
expect "Create unauthorized" "loans" "POST" "/loans" "" "{\"book_id\":$BOOK_ID}" "401" '.error' 'unauthorized' >/dev/null
expect "Create missing fields" "loans" "POST" "/loans" "$TEST_ACCESS_TOKEN" '{}' "400" '.error' 'missing_fields' >/dev/null
expect "Invalid loan_days type" "loans" "POST" "/loans" "$TEST_ACCESS_TOKEN" "{\"book_id\":$BOOK_ID,\"loan_days\":\"xx\"}" "400" '.error' 'invalid_loan_days' >/dev/null
expect "Invalid loan_days value" "loans" "POST" "/loans" "$TEST_ACCESS_TOKEN" "{\"book_id\":$BOOK_ID,\"loan_days\":0}" "400" '.error' 'invalid_loan_days' >/dev/null
expect "Extend not found" "loans" "POST" "/loans/999999/extend" "$TEST_ACCESS_TOKEN" '{"extra_days":3}' "404" '.error' 'loan_not_found' >/dev/null
expect "Return not found" "loans" "POST" "/loans/999999/return" "$TEST_ACCESS_TOKEN" "" "404" '.error' 'loan_not_found' >/dev/null

LOAN_CREATE_BODY="$(expect "Create loan book-level" "loans" "POST" "/loans" "$TEST_ACCESS_TOKEN" "{\"book_id\":$BOOK_ID,\"loan_days\":7}" "201")"
NEW_LOAN_ID="$(echo "$LOAN_CREATE_BODY" | jq -r '.loan_id')"
info "Created loan ID=$NEW_LOAN_ID"

expect "List self active loans" "loans" "GET" "/users/$TEST_USER_ID/loans?active=true" "$TEST_ACCESS_TOKEN" "" "200" >/dev/null

SECOND_EMAIL="autotest2_${TS}@example.com"
expect "Second user register" "loans" "POST" "/register" "" "{\"email\":\"$SECOND_EMAIL\",\"password\":\"secret123\",\"name\":\"User2\",\"address\":\"Addr\",\"date_of_birth\":\"2001-01-01\"}" "201" >/dev/null
LOGIN2="$(expect "Second user login" "loans" "POST" "/login" "" "{\"email\":\"$SECOND_EMAIL\",\"password\":\"secret123\"}" "200")"
TOKEN2="$(echo "$LOGIN2" | jq -r '.access_token')"
USER2_ID="$(echo "$LOGIN2" | jq -r '.user.user_id')"
info "Second user id=$USER2_ID"

expect "Member cannot view other loans" "loans" "GET" "/users/$USER2_ID/loans?active=true" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "Admin view user1 loans" "loans" "GET" "/users/$TEST_USER_ID/loans?active=true" "$ADMIN_ACCESS_TOKEN" "" "200" >/dev/null

expect "Extend missing extra_days" "loans" "POST" "/loans/$NEW_LOAN_ID/extend" "$TEST_ACCESS_TOKEN" '{}' "400" '.error' 'invalid_extra_days' >/dev/null
expect "Extend non-int" "loans" "POST" "/loans/$NEW_LOAN_ID/extend" "$TEST_ACCESS_TOKEN" '{"extra_days":"x"}' "400" '.error' 'invalid_extra_days' >/dev/null
expect "Extend non-positive" "loans" "POST" "/loans/$NEW_LOAN_ID/extend" "$TEST_ACCESS_TOKEN" '{"extra_days":0}' "400" '.error' 'invalid_extra_days' >/dev/null
expect "Extend forbidden other user" "loans" "POST" "/loans/$NEW_LOAN_ID/extend" "$TOKEN2" '{"extra_days":3}' "403" '.error' 'forbidden' >/dev/null
expect "Extend OK" "loans" "POST" "/loans/$NEW_LOAN_ID/extend" "$TEST_ACCESS_TOKEN" '{"extra_days":5}' "200" >/dev/null
expect "Return OK" "loans" "POST" "/loans/$NEW_LOAN_ID/return" "$TEST_ACCESS_TOKEN" "" "200" >/dev/null
expect "Return already returned" "loans" "POST" "/loans/$NEW_LOAN_ID/return" "$TEST_ACCESS_TOKEN" "" "400" '.error' 'loan_already_returned' >/dev/null

LOAN2_CREATE_BODY="$(expect "Create loan user2" "loans" "POST" "/loans" "$TOKEN2" "{\"book_id\":$BOOK_ID,\"loan_days\":7}" "201")"
LOAN2_ID="$(echo "$LOAN2_CREATE_BODY" | jq -r '.loan_id')"
expect "Return forbidden other user's loan" "loans" "POST" "/loans/$LOAN2_ID/return" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "Return OK user2" "loans" "POST" "/loans/$LOAN2_ID/return" "$TOKEN2" "" "200" >/dev/null
expect "Overdue member forbidden" "loans" "GET" "/loans/overdue" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "Overdue admin OK" "loans" "GET" "/loans/overdue" "$ADMIN_ACCESS_TOKEN" "" "200" >/dev/null

############################################################
# Section: Reservations
############################################################
section_header "Reservations"
expect "Create unauthorized" "reservations" "POST" "/reservations" "" "{\"book_id\":$BOOK_ID}" "401" '.error' 'unauthorized' >/dev/null
expect "Missing fields" "reservations" "POST" "/reservations" "$TEST_ACCESS_TOKEN" '{}' "400" '.error' 'missing_fields' >/dev/null
expect "Invalid book_id type" "reservations" "POST" "/reservations" "$TEST_ACCESS_TOKEN" '{"book_id":"x"}' "400" '.error' 'invalid_ids' >/dev/null

RES_CREATE_BODY="$(expect "Create reservation user1" "reservations" "POST" "/reservations" "$TEST_ACCESS_TOKEN" "{\"book_id\":$BOOK_ID}" "201")"
RES_ID="$(echo "$RES_CREATE_BODY" | jq -r '.reservation_id')"
info "Reservation ID=$RES_ID"

expect "List self reservations" "reservations" "GET" "/users/$TEST_USER_ID/reservations?status=all" "$TEST_ACCESS_TOKEN" "" "200" >/dev/null
expect "Invalid status filter" "reservations" "GET" "/users/$TEST_USER_ID/reservations?status=foo" "$TEST_ACCESS_TOKEN" "" "400" '.error' 'invalid_status' >/dev/null
expect "List other user forbidden" "reservations" "GET" "/users/$USER2_ID/reservations?status=all" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "List for book forbidden (member)" "reservations" "GET" "/books/$BOOK_ID/reservations" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "List for book admin OK" "reservations" "GET" "/books/$BOOK_ID/reservations" "$ADMIN_ACCESS_TOKEN" "" "200" >/dev/null

expect "Update invalid status" "reservations" "POST" "/reservations/$RES_ID/status" "$ADMIN_ACCESS_TOKEN" '{"status":"invalid"}' "400" '.error' 'invalid_status' >/dev/null
expect "Update ready" "reservations" "POST" "/reservations/$RES_ID/status" "$ADMIN_ACCESS_TOKEN" '{"status":"ready"}' "200" '.status' 'ready' >/dev/null
expect "Cancel forbidden other user" "reservations" "POST" "/reservations/$RES_ID/cancel" "$TOKEN2" "" "403" '.error' 'forbidden' >/dev/null
expect "Cancel own -> expired" "reservations" "POST" "/reservations/$RES_ID/cancel" "$TEST_ACCESS_TOKEN" "" "200" '.status' 'expired' >/dev/null
expect "Cancel invalid ID 404" "reservations" "POST" "/reservations/999999/cancel" "$TEST_ACCESS_TOKEN" "" "404" '.error' 'reservation_not_found' >/dev/null
expect "Status change invalid ID 404" "reservations" "POST" "/reservations/999999/status" "$ADMIN_ACCESS_TOKEN" '{"status":"ready"}' "404" '.error' 'reservation_not_found' >/dev/null

RES2_CREATE_BODY="$(expect "Create reservation user2" "reservations" "POST" "/reservations" "$TOKEN2" "{\"book_id\":$BOOK_ID}" "201")"
RES2_ID="$(echo "$RES2_CREATE_BODY" | jq -r '.reservation_id')"
expect "Admin cancel other user's reservation" "reservations" "POST" "/reservations/$RES2_ID/cancel" "$ADMIN_ACCESS_TOKEN" "" "200" '.status' 'expired' >/dev/null

############################################################
# Section: Admin
############################################################
section_header "Admin"
expect "Stats unauthorized no token" "admin" "GET" "/admin/stats" "" "" "401" '.error' 'unauthorized' >/dev/null
expect "Stats member forbidden" "admin" "GET" "/admin/stats" "$TEST_ACCESS_TOKEN" "" "403" '.error' 'forbidden' >/dev/null
expect "Stats OK admin" "admin" "GET" "/admin/stats" "$ADMIN_ACCESS_TOKEN" "" "200" >/dev/null

############################################################
# Section: Logout (végére téve)
############################################################
section_header "Logout"
expect "Logout OK" "logout" "POST" "/logout" "$TEST_ACCESS_TOKEN" "" "200" '.status' 'ok' >/dev/null
expect "Me after logout revoked" "logout" "GET" "/me" "$TEST_ACCESS_TOKEN" "" "401" >/dev/null

############################################################
# Per-section summary
############################################################
log "\n${BOLD}Section summaries:${RESET}"
for S in health auth ratelimit users books loans reservations admin logout; do
  log "$(printf '%-13s' "$S"): ${SEC_PASS[$S]}/${SEC_TOTAL[$S]} passed, ${SEC_FAIL[$S]} failed"
done

############################################################
# Global summary
############################################################
echo "" | tee -a "$OUT_FILE"
if [[ $FAILED -eq 0 ]]; then
  log "${GREEN}${BOLD}SUCCESS${RESET} All $PASSED/$TOTAL tests passed."
  echo -e "${GREEN}${BOLD}Summary:${RESET} $PASSED/$TOTAL passed, $FAILED failed."
else
  log "${RED}${BOLD}SOME TESTS FAILED${RESET} $PASSED/$TOTAL passed, $FAILED failed."
  echo -e "${RED}${BOLD}Summary:${RESET} $PASSED/$TOTAL passed, $FAILED failed."
  exit 1
fi
