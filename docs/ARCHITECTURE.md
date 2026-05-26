# Architecture decisions

This is the "why" file. Every load-bearing choice we made at the init lives
here so that six months from now, "why did we do it this way?" has an answer.
Add a new section every time we make another big call.

---

## 1. Vertical-slice teams, not layer teams

Each developer owns a **full feature end-to-end** (API + UI + DB + tests +
docs) instead of being "the backend person" or "the frontend person".

**Why:** zero hand-offs, no "I'm blocked on someone else's PR", every PR is
demoable. Layer teams scale to companies; for a 4-person student squad they
just create bottlenecks.

**Trade-off:** shared data models (like `accounts.User`, `appointments.Appointment`)
have **one owner** — you negotiate cross-slice changes in chat before you
push. See `.github/CODEOWNERS`.

## 2. Custom `User` model from minute zero

`AUTH_USER_MODEL = 'accounts.User'` is set in the very first migration.

**Why:** adding a custom user model AFTER the first migration is famously
painful in Django (you'd be rewriting every FK). Cheap insurance.

Implementation: `accounts.User` extends `AbstractUser`, drops the `username`
field, and uses `email` as `USERNAME_FIELD`. Custom `UserManager` knows how
to create users without a username.

## 3. Doctor = `OneToOneField` subtype of User (ISA via class-table inheritance)

In the ERD, "Doctor is a User where role=doctor". In Django, the two ways to
express that are:

1. **Multi-table inheritance** — `class Doctor(User)`. Implicit JOIN on every
   doctor query. Well-known footgun.
2. **`OneToOneField(..., primary_key=True)`** — a separate `DoctorProfile`
   table whose PK is the user's PK. Explicit, queryable both ways, no surprise
   JOINs.

We picked **(2)**. `accounts.User` stays clean; `doctors.DoctorProfile`
carries `specialty`, `resume_url`, `license_url`, `hourly_rate`. A row exists
IFF `User.role == 'doctor'`.

This mirrors the mermaid `USER ||--o| DOCTOR` relationship in the frontend
ERD. Patient and admin records live only in `User`.

## 4. SimpleJWT for stateless auth (not session cookies)

The React SPA is a separate origin. JWT in `Authorization: Bearer …` works
across origins without CSRF complications and lets us scale horizontally
later without sticky sessions.

- Access token: 1 hour.
- Refresh token: 7 days, **rotated** on each use (and the old one is
  immediately invalid).
- Login endpoint accepts `email` + `password` — SimpleJWT picks up our
  `USERNAME_FIELD='email'` automatically.

## 5. Settings split: `base.py` / `dev.py` / `prod.py`

One `settings.py` shared by four developers = a daily merge conflict. The
split:

- `base.py` — everything common, env-driven.
- `dev.py` — `DEBUG=True`, permissive `ALLOWED_HOSTS`. Default for
  `manage.py` and `runserver`.
- `prod.py` — strict, fails loud on missing env vars, HTTPS-only cookies.

Switch with `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## 6. SQLite in dev, Postgres in prod, swap via `DATABASE_URL`

Day-zero clone has to work with no Postgres install. We default to SQLite at
`./db.sqlite3`. Production sets `DATABASE_URL=postgres://…` in the env and
the same code runs against Postgres — `psycopg[binary]` is already in
`requirements.txt`.

**Heads-up:** SQLite's locking is per-write. If two developers' tests fight
each other in CI we'll move CI to Postgres.

## 7. API versioning at `/api/v1/` from the start

Every URL is mounted under `/api/v1/<app>/`. Breaking the contract later
means `/api/v2/`, not "we broke production at 3 AM".

## 8. CORS locked down by env, not wide open

`CORS_ALLOWED_ORIGINS` is read from env (default = the Vite dev server). We
do **not** set `CORS_ALLOW_ALL_ORIGINS = True` — even in dev, the explicit
list catches typos and makes the prod contract obvious.

## 9. `core/permissions.py` is the one source of truth for role checks

`IsAdmin`, `IsDoctor`, `IsApprovedDoctor`, `IsPatient`, `IsOwnerOrAdmin` —
defined once, imported by every app. "What is an approved doctor?" must have
exactly one answer in the codebase.

## 10. `resume_url` / `license_url` are `TextField`, not `URLField`

The React app may send either a real https link OR a base64 `data:` URL when
the doctor uploaded a file directly. `URLField`'s validator rejects the
latter. We accept both at the model layer and validate at the serializer
boundary. Replace with real `FileField` + storage when we add S3.

## 11. DB-level `UniqueConstraint` against double-booking

`Appointment` has `UniqueConstraint(doctor, date, time)`. The race condition
between two simultaneous booking requests is impossible at the DB layer —
not just at the application layer (where it's a TOCTOU bug waiting to
happen).

## 12. Initial migrations are committed by the init PR

If each app owner ran `makemigrations` independently, we'd have four
conflicting `0001_initial.py` files. Shipping them in the init means every
clone migrates cleanly from the same baseline.
