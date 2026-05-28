# RESTCareFul — ER Diagram (Mermaid)

The data model behind this Django backend (shared with the
[useCare](https://github.com/DevAbdoTolba/useCare) React frontend). The drawio
source is [`ERD.drawio`](./ERD.drawio) — open it in [diagrams.net](https://app.diagrams.net)
and look at the **"ERD — post-discussion"** page, which is the one these Django
models implement. The three original entities (User / Specialty / Appointments)
keep the diagram's field names (`U_*`, `S_*`, `A_*`).

Everything tagged **(post-discussion)** was added after the lecturer review:
the new **Doctor** subtype (ISA of `User` when `U_role = 'doctor'`) holding all
doctor-only fields, plus the new Rating, Payment, SpecialtySuggestion and
DocUpdateRequest entities.

> **Image note:** [`ERD-original.png`](./ERD-original.png) is a PNG export of
> the *original* (pre-post-discussion) diagram page — it does **not** show the
> Doctor subtype / Payment / Rating entities. A fresh export of the
> "ERD — post-discussion" page still needs to be dropped in as `ERD.png`
> (export from diagrams.net: File → Export as → PNG). The Mermaid diagram
> below and `ERD.drawio` are the up-to-date sources of truth.

```mermaid
erDiagram
    USER ||--o| DOCTOR : "is a (when U_role=doctor)"
    SPECIALTY ||--o{ DOCTOR : "has (N:1)"
    USER ||--o{ APPOINTMENTS : "books — patient (1:N)"
    DOCTOR ||--o{ APPOINTMENTS : "manages (1:N)"

    APPOINTMENTS ||--o| RATING : "rated after completion (1:0..1)"
    DOCTOR ||--o{ RATING : "receives (1:N)"
    USER ||--o{ RATING : "leaves — patient (1:N)"

    APPOINTMENTS ||--o| PAYMENT : "paid for (1:0..1)"
    USER ||--o{ PAYMENT : "pays — patient (1:N)"

    DOCTOR ||--o{ SPECIALTY_SUGGESTION : "proposes (1:N)"
    SPECIALTY_SUGGESTION }o--|| SPECIALTY : "becomes on approval"

    DOCTOR ||--o{ DOC_UPDATE_REQUEST : "requests (1:N)"

    USER {
        int U_id PK
        string U_name
        string U_role
        string U_email
        string U_password
        date U_DoB
        string U_gender
        string u_phone_number
        string U_Desc
        string U_status "post-discussion"
    }

    DOCTOR {
        int D_id PK,FK "post-discussion: = U_id (both PK and FK to User)"
        int specialty_id FK
        string D_resume_url "post-discussion: link or data URL"
        string D_license_url "post-discussion: link or data URL"
        float D_hourly_rate "post-discussion (USD)"
    }

    SPECIALTY {
        int S_id PK
        string S_name
        string S_desc
    }

    APPOINTMENTS {
        int A_id PK
        date A_date
        time A_time
        string A_notes
        string A_status
        boolean A_paid "post-discussion"
        float A_amount_paid "post-discussion (USD)"
        int patient_id FK
        int doctor_id FK
    }

    RATING {
        int appointment_id PK,FK
        int doctor_id FK
        int patient_id FK
        int stars "1..5"
        string comment "optional — why this rating"
    }

    PAYMENT {
        int id PK
        int appointment_id FK
        int patient_id FK
        int doctor_id FK
        float amount "USD"
        string status "paid / refunded"
        date date
    }

    SPECIALTY_SUGGESTION {
        int id PK
        string name "proposed specialty"
        string proposed_by "doctor email"
        string status "pending / approved / rejected"
    }

    DOC_UPDATE_REQUEST {
        int id PK
        int doctor_id FK
        string doctor_name "denormalised for the admin list"
        string resume_url "proposed — link or data URL (uploaded file)"
        string license_url "proposed — link or data URL (uploaded file)"
        string status "pending / approved / rejected"
    }
```

## Relationships

| From | To | Verb | Cardinality |
|------|----|------|-------------|
| User | Doctor | ISA | every User with `role=doctor` has exactly one Doctor row; patient and admin users have none *(post-discussion: class-table inheritance — `D_id = U_id`)* |
| Doctor | Specialty | Has | many doctors → one specialty *(post-discussion: moved off User, since only doctors have a specialty)* |
| User | Appointments | Book | one patient → many appointments |
| Doctor | Appointments | Manage | one doctor → many appointments *(post-discussion: moved off User)* |
| Appointments | Rating | Rated | each completed appointment → at most one rating *(post-discussion)* |
| Doctor | Rating | Receives | a doctor receives many ratings *(post-discussion)* |
| User | Rating | Leaves | a patient leaves many ratings *(post-discussion)* |
| Appointments | Payment | Paid for | each appointment → at most one payment *(post-discussion)* |
| User | Payment | Pays | one patient → many payments; platform keeps a 12% cut *(post-discussion)* |
| Doctor | SpecialtySuggestion | Proposes | a doctor proposes specialties the admin approves into Specialty *(post-discussion)* |
| Doctor | DocUpdateRequest | Requests | a doctor files résumé/license changes the admin approves back onto Doctor *(post-discussion)* |

## Notes on the additions

- **Doctor (ISA subtype of User)** — **class-table inheritance**: every Doctor
  row has `D_id = U_id` (both PK *and* FK to `User`). Patient and admin records
  live only in `User`; users with `role=doctor` get an extra `Doctor` row that
  holds the doctor-only attributes. All relationships that only make sense for
  a doctor (`Has` specialty, `Manage` appointments, `Receives` ratings,
  `Proposes` SpecialtySuggestion, `Requests` DocUpdateRequest) hang off
  `Doctor`, not `User`.
- **D_resume_url / D_license_url** — required at doctor signup; the admin opens
  both before approving or rejecting the account. Each field stores either a
  link (`https://…`) or a `data:` URL when the doctor uploaded a file directly.
- **D_hourly_rate** — the consultation fee shown to patients and charged
  through the PayPal sandbox at booking time.
- **Payment** — `amount_paid` on the appointment is the per-booking record;
  `Payment` rows are the ledger the admin dashboard sums (total paid + 12%
  platform revenue).
- **SpecialtySuggestion** — a doctor whose specialty isn't listed proposes one;
  approving it creates a real `Specialty`.
- **DocUpdateRequest** — already-approved doctors can't silently swap their
  résumé/license. They file a `DocUpdateRequest`; admin approval patches the
  matching `D_resume_url` / `D_license_url` back onto `Doctor`.
