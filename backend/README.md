# Könyvtár API – Backend (Flask, PostgreSQL)

[![Backend CI (na-backend)](https://github.com/zsofa/library-webapp/actions/workflows/backend-ci.yml/badge.svg?branch=na-backend)](https://github.com/zsofa/library-webapp/actions/workflows/backend-ci.yml?query=branch%3Ana-backend)

Ez a mappa a könyvtárkezelő rendszer backendje. Cél: stabil, jól tesztelt REST API, ami egyszerűen illeszthető a frontendhez.

## Fő képességek
- JWT alapú autentikáció (access + refresh), logout (JTI blocklist, memóriában)
- Jelszó policy (min. 8 karakter, betű + szám) + “silent rehash” (régi MD5 → PBKDF2 frissítés login közben)
- Könyvek listázása / keresése / kategória szűrés / lapozás; könyv részlete és elérhető példányok számítása
- Kölcsönzések (item- és könyv-szinten), hosszabbítás, visszahozás, user- és admin-nézetek, overdue lista (admin)
- Foglalások (várólista), státuszváltás (admin), cancel, tömeges expire (admin)
- Admin statisztika
- Egységes JSON hibaválaszok request_id-vel
- /login rate limit (IP + email)

Monorepo felosztás: `frontend/` • `db/` • `backend/` (ez a dokumentum csak a backendre vonatkozik).

---

## Gyors indítás (lokális)

1. Függőségek és virtualenv

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Környezeti változók

   ```bash
   cp .env.example .env
   # Szerkeszd a szükséges értékeket (JWT_SECRET_KEY, CORS_ORIGINS, DB_* stb.)
   ```
   A `.env.example` fájl tartalmaz egy alap konfigurációt; érdemes ebből kiindulni és a saját értékeket itt módosítani.

3. Szerver indítása

   ```bash
   python app.py
   # Base: http://localhost:5000
   # API:  http://localhost:5000/api
   ```

Megjegyzés: az adatbázis sémát és inicializálást a `db/` mappa csapatkezeli (itt nem módosítjuk).

---

## Fontos a frontend integrációhoz
- Auth header: `Authorization: Bearer <access_token>`
- Refresh: `POST /api/token/refresh` (refresh tokennel)
- Hibák: egységes JSON (error, message, meta.request_id)
- Kérésazonosító: minden válaszban `X-Request-ID`, hibáknál meta.request_id
- CORS: `.env` `CORS_ORIGINS` (pl. `http://localhost:3000`)
- Pagináció: `/books` → `page` (default 1), `page_size` (default 20, max 100)
- `/users/{id}/loans`: `active=true|false|all` (default: true), `overdue=true|false` (default: false)
- Jelszó policy megsértésekor `meta.violations` listát ad (pl. `["min_length_8","must_include_digit"]`)

---

## Gyors API példák (curl)

- Regisztráció

  ```bash
  curl -X POST http://localhost:5000/api/register \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"Strong123","name":"User","address":"Addr","date_of_birth":"2000-01-01"}'
  ```

- Login

  ```bash
  curl -X POST http://localhost:5000/api/login \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"Strong123"}'
  # Válasz: access_token, refresh_token
  ```

- Könyv-szintű kölcsönzés

  ```bash
  curl -X POST http://localhost:5000/api/loans \
    -H "Authorization: Bearer ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"book_id":5,"loan_days":7}'
  ```

- Foglalás

  ```bash
  curl -X POST http://localhost:5000/api/reservations \
    -H "Authorization: Bearer ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"book_id":5}'
  ```

- Admin statisztika

  ```bash
  curl -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
    http://localhost:5000/api/admin/stats
  ```

---

## Endpointok (rövidített áttekintés)

Health / dokumentáció
- GET `/api/health`
- GET `/api/openapi.yaml` (ha a fájl jelen van)

Auth
- POST `/api/register`
- POST `/api/login`
- POST `/api/token/refresh`
- POST `/api/logout`
- GET `/api/me`
- POST `/api/me/password`

Books
- GET `/api/books?q=&category=&library_id=&page=&page_size=`
- GET `/api/books/{book_id}?library_id=`

Loans
- POST `/api/loans`
- POST `/api/loans/{loan_id}/extend`
- POST `/api/loans/{loan_id}/return`
- GET `/api/users/{user_id}/loans?active=true|false|all&overdue=true|false`
- GET `/api/loans/overdue` (admin)

Reservations
- POST `/api/reservations`
- GET `/api/users/{user_id}/reservations?status=all|pending|ready|expired|fulfilled`
- GET `/api/books/{book_id}/reservations` (admin)
- POST `/api/reservations/{reservation_id}/status` (admin)
- POST `/api/reservations/{reservation_id}/cancel`
- POST `/api/admin/reservations/expire` (admin)

Users
- GET `/api/users/{user_id}`
- PUT `/api/users/{user_id}`

Admin
- GET `/api/admin/stats`

Részletek: lásd `openapi.yaml` és a route fájlok kommentjei.

---

## Gyakoribb hibakódok
missing_fields, invalid_date_of_birth, weak_password, email_exists
missing_credentials, invalid_credentials, too_many_attempts
unauthorized, token_expired, token_revoked
forbidden, not_found, book_not_found, item_not_found
loan_not_found, loan_already_returned, loan_overdue, invalid_loan_days, invalid_extra_days, no_available_item, different_library
reservation_not_found, reservation_exists, invalid_status
no_fields_to_update, db_error, server_error

Minden hiba: egységes JSON + `meta.request_id`.

---

## Konkurencia / robusztusság
- Könyv-szintű kölcsönzés: `FOR UPDATE SKIP LOCKED` → párhuzamos kérések nem választják ugyanazt az itemet.
- Foglalás queue_number: lock + `MAX(queue_number)+1` + korlátozott retry UniqueViolation-ra.
- /login rate limit: IP+email kulcs, csúszó időablak (env-ben paraméterezhető).

---

## Tesztelés (lokális eredmények)

API test (tests/run_api_tests.sh):
```
Section summaries:
health       : 3/3 passed, 0 failed
auth         : 8/8 passed, 0 failed
ratelimit    : 14/14 passed, 0 failed
users        : 7/7 passed, 0 failed
books        : 4/4 passed, 0 failed
loans        : 21/21 passed, 0 failed
reservations : 15/15 passed, 0 failed
admin        : 3/3 passed, 0 failed
logout       : 2/2 passed, 0 failed

SUCCESS All 77/77 tests passed.
Summary: 77/77 passed, 0 failed.
```

Pytest (unit/integration):
```
98 passed in 3.50s
```

Coverage összefoglaló:
```
TOTAL 1761 stmts, 117 miss, 93%
(db.py alacsony lefedettség szándékos)
```

---

## CI (GitHub Actions)
- Workflow: `.github/workflows/backend-ci.yml`
- Trigger: push / PR a `na-backend` branchre → csak akkor fut, ha érinti a `backend/**` mappát (vagy kézi indítás).
- Lépések: setup Python → install → pytest + coverage (küszöb: 85%).
- A badge jelenleg a `na-backend` branch állapotát mutatja; main merge után cserélhető.

---

## Környezeti változók (áttekintés)
Flask/JWT: `SECRET_KEY`, `JWT_SECRET_KEY`, `JWT_EXPIRES_HOURS`, `JWT_REFRESH_EXPIRES_DAYS`
CORS: `CORS_ORIGINS`
DB: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
Alapértékek: `DEFAULT_LOAN_DAYS`, `RESERVATION_EXPIRY_DAYS`, `DEFAULT_LIBRARY_ID`, `DEFAULT_MEMBER_ROLE_ID`
Rate limit: `LOGIN_RATE_LIMIT_ATTEMPTS`, `LOGIN_RATE_LIMIT_WINDOW_S`
Debug: `FLASK_DEBUG`

Ha hiányzik valamelyik, a kód defaultot használ.

---

## Fájlok és szerepük (backend)
- `app.py` – Flask init, JWT, CORS, hibakezelők, blueprint regisztráció
- `auth_routes.py` – regisztráció, login, refresh, logout, /me, jelszócsere
- `book_routes.py` – könyv lista + részletek (elérhető példány számítás)
- `loan_routes.py` – kölcsönzés, hosszabbítás, visszahozás, listázás, overdue
- `reservation_routes.py` – foglalás, státusz, cancel, expire
- `user_routes.py` – profil lekérdezés/módosítás
- `admin_routes.py` – statisztikák
- `auth_utils.py` – @login_required, @role_required, /login rate limit logika
- `db.py` – psycopg2 kapcsolat + UTC timezone
- `parse_utils.py` – `ParseError`, parse_int/date, require_fields
- `password_utils.py` – PBKDF2 hash + MD5 fallback verify
- `password_policy.py` – jelszó szabályok
- `response_utils.py` – egységes hiba JSON
- `openapi.yaml` – OpenAPI 3.0 specifikáció
- `postman_collection.json` – Postman kollekció
- `tests/run_api_tests.sh` – fekete-doboz API script
- `tests/` – pytest modulok

---
