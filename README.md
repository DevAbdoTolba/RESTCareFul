# RESTCareFul

Django + DRF backend for the [useCare](https://github.com/DevAbdoTolba/useCare) React
frontend. Same domain (medical appointment booking), now with a real database, real
auth, and a real PayPal integration on the way.

## Stack

- **Django 5** + **Django REST Framework**
- **SimpleJWT** for stateless auth (React SPA reads `access` + `refresh` tokens)
- **SQLite** in dev, **Postgres** in prod (`DATABASE_URL` env var swaps it)
- **django-environ** for config, **django-cors-headers** for the Vite dev server
- **pytest-django** + **factory_boy** for tests, **ruff** for lint + format

## Quickstart

```bash
git clone https://github.com/DevAbdoTolba/RESTCareFul.git
cd RESTCareFul
python -m venv venv
# Windows
./venv/Scripts/activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env             # then edit DJANGO_SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API now answers at `http://localhost:8000/api/v1/`. Try it:

```bash
# Register a patient
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"yara@usecare.test","password":"patient123","role":"patient","first_name":"Yara"}'

# Log in (returns access + refresh JWTs)
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"yara@usecare.test","password":"patient123"}'

# Use the access token
curl http://localhost:8000/api/v1/auth/me/ \
  -H 'Authorization: Bearer <access-token>'
```

## Project layout

```
config/                 Django project (settings split: base / dev / prod)
accounts/               Custom User model + auth endpoints     (Tolba)
core/                   Shared DRF permissions, base classes   (Tolba)
doctors/                DoctorProfile (ISA subtype), availability (Fathi)
specialties/            Specialty + suggestion flow            (Samir)
appointments/           Appointment lifecycle                  (Samir)
payments/               PayPal ledger + capture                (Hany)
ratings/                Rate doctors after completed visits    (Tolba)
dashboard/              Admin metrics aggregation              (Hany)
docs/ARCHITECTURE.md    Why we made the decisions we made
CONTRIBUTING.md         How the team works
.github/CODEOWNERS      Who reviews what
```

Each top-level app is one **vertical slice** owned end-to-end (model →
serializer → view → URL → test → docs) by one person. See
[`CONTRIBUTING.md`](./CONTRIBUTING.md) before you push your first PR.

## Workflow at a glance

1. Pick (or open) an issue.
2. Branch off `main`: `feat/<slice>-<short-desc>`.
3. Push, open a PR (draft is fine).
4. CI runs (`ruff` + `pytest`). Must be green.
5. One peer review, then merge.
6. **Nobody pushes to `main` directly.**

The long version lives in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Why the architecture is the way it is

The load-bearing decisions (vertical slicing, custom User from day one, Doctor
as an ISA subtype via `OneToOneField`, JWT, settings split, …) are documented
in [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md). Read it once — it explains
the *why* behind anything that looks unusual.

## Frontend

The React SPA that consumes this API lives at
[useCare](https://github.com/DevAbdoTolba/useCare). The Vite dev server origin
(`http://localhost:5173`) is allow-listed in `CORS_ALLOWED_ORIGINS` by default.

## Team

- [@Ahmed Fathi](https://github.com/AhmeedFatehy) — `doctors`
- [@Abdo Tolba](https://github.com/DevAbdoTolba) — `accounts`, `core`, `ratings`
- [@Ahmed Samir](https://github.com/AhmedSamirKhalaf) — `appointments`, `specialties`
- Hany — `payments`, `dashboard`
