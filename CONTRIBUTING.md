# Contributing to RESTCareFul

This is how we work as a team. Read it once before you push your first PR.

---

## How we ship: vertical slices + GitHub flow

We are **not** split by layer (one backend, one frontend, one DB person). Each
developer owns **a full feature, end-to-end** — the API, the React UI that
calls it, the migrations, the tests, the docs.

**Why:** fewer hand-offs, no "I'm blocked on the API person", every PR can be
demoed on its own.

The trade-off: shared models (like `accounts.User` or `appointments.Appointment`)
have **one owner** — change them only after a quick chat with that owner. See
`.github/CODEOWNERS` for who that is.

### Ownership map

| Vertical slice | Owner | Backend app | Frontend area (useCare) |
|---|---|---|---|
| Auth, profile, current-user | Tolba | `accounts/`, `core/` | `src/auth/`, `src/pages/auth/`, `ProfilePage` |
| Doctor profile + availability | Fathi | `doctors/` | `DoctorCalendarPage` |
| Appointment lifecycle | Samir | `appointments/` | `MyAppointmentsPage`, booking dialog |
| Specialties + suggestions | Samir | `specialties/` | `SpecialtiesPage`, suggest UI |
| Payments + revenue | Hany | `payments/` | PayPal flow, admin revenue card |
| Admin dashboard metrics | Hany | `dashboard/` | `AdminDashboardPage` |
| Ratings | Tolba | `ratings/` | rate-after-completion UI |

If your work touches another slice, **open a tiny PR against that slice's
owner first**, then build your feature on top.

---

## Day-zero setup

```bash
git clone https://github.com/DevAbdoTolba/RESTCareFul.git
cd RESTCareFul
python -m venv venv
# Windows
./venv/Scripts/activate
# macOS / Linux
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit DJANGO_SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Defaults to SQLite — zero install. Switch to Postgres later by setting
`DATABASE_URL=postgres://…` in `.env`.

---

## The Git rules (non-negotiable)

1. **`main` is protected.** Nobody pushes directly. Ever.
2. **One branch per feature.** Name it `feat/<slice>-<short-desc>` or
   `fix/<slice>-<short-desc>`. Examples: `feat/doctors-set-availability`,
   `fix/appointments-cancel-race`.
3. **Open a PR early** (draft is fine) so the team sees what you're working
   on — prevents two people from grabbing the same slot of work.
4. **Small PRs win.** Target < 400 added lines. If it's bigger, split it.
5. **One PR = one concern.** Don't bundle a refactor with a feature.
6. **Rebase, don't merge `main` into your branch.**
   `git pull --rebase origin main` before pushing.
7. **CI must be green before merge.** No "merge it anyway".
8. **At least one approving review** required.

### Commit messages

Use **conventional commits**:

```
<type>(<scope>): <imperative summary>

type: feat | fix | refactor | docs | chore | ci | test
scope: the app or area (accounts, doctors, ci, docs, …)
```

Examples:

```
feat(doctors): expose POST /api/v1/doctors/me/availability
fix(appointments): block double-booking the same slot
refactor(core): extract IsApprovedDoctor permission
```

Use the body for the *why*; the diff already shows the *what*.

---

## Reviewing someone else's PR

You review **at least one PR per day** when there's something in the queue —
that's how we keep velocity up.

When you review, check:

- [ ] **Correctness.** Does it do what the issue says?
- [ ] **Tests.** New code has at least a happy-path test.
- [ ] **Migrations.** No conflicting `0001_initial.py`. Only one migration per
      PR unless the change genuinely needs more.
- [ ] **Boundaries.** No cross-slice writes. If `doctors` is suddenly editing
      `Appointment` rows directly, flag it.
- [ ] **Secrets.** Nothing committed that belongs in `.env`.
- [ ] **Naming.** `URL` vs `data URL`, `paid` vs `is_paid`, etc. — stay
      consistent with what already exists.

Approve only if you'd be willing to be on-call for the change.

---

## Avoiding merge conflicts

The init was deliberately structured to make conflicts rare:

- **One owner per app.** No two people edit the same `models.py` at the same
  time.
- **`config/settings/base.py` is high-friction territory.** Don't edit it for
  feature work; if you absolutely must add a setting, ping the team in chat
  first.
- **`config/urls.py` is mounted per-app.** Adding a new app's URL is one line
  there — coordinate the line addition in chat to avoid two PRs editing the
  same line.

If you do hit a conflict, **rebase**, fix it locally, and force-push with
`--force-with-lease` (NEVER plain `--force`).

---

## Tests

- `pytest` from the repo root runs everything.
- Tests live per-app: `appointments/tests/` etc.
- Use `factory_boy` factories for objects, not hand-built dicts.
- Don't mock the database in integration tests — hit the real (SQLite) one.

A PR that touches behaviour without a test is a PR that gets sent back.

---

## Linting / formatting

```bash
ruff check .              # lint
ruff format .             # autoformat
```

Both run on every PR via GitHub Actions. Fix locally before pushing —
"fix lint" commits in a PR are noise.

---

## Architecture decisions (ADRs)

`docs/ARCHITECTURE.md` records the *why* behind the load-bearing decisions
(custom User, ISA Doctor pattern, JWT, vertical slicing). Update it when you
make another one — six months from now, "why did we do it this way?" is the
question that costs most.
