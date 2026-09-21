# Offline AI Hospital Management System

A two-tier hospital patient system built for low-connectivity clinics:

- **Local app** (`app.py`, port 5000) — runs at the clinic, works fully offline.
  Registers patients, runs a rule-based "AI" triage, and stores everything in
  a local SQLite database (`hospital.db`).
- **Central server** (`server.py`, port 5001) — represents a central/hospital
  database. The local app syncs newly registered patients to it automatically
  every 10 seconds whenever it's reachable, and keeps retrying if it isn't.

## Project structure

```
app.py              # Local Flask app: registration, triage, appointments,
                     #   FAQ assistant, dashboard, sync client
server.py            # Central Flask server: receives synced patient/appointment records
templates/
  dashboard.html      # Doctor dashboard (patient list, priority counts)
  register.html        # Patient registration form
  appointment.html      # Appointment booking form
  assistant.html         # Offline FAQ assistant chat UI
hospital.db           # Local SQLite database (created automatically if missing)
server.db             # Central SQLite database (created automatically if missing)
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Running it

Start the central server first, then the local app, in two separate terminals:

```bash
python3 server.py      # http://127.0.0.1:5001
python3 app.py          # http://127.0.0.1:5000
```

Then open:

- **Register a patient:** http://127.0.0.1:5000/register
- **Book an appointment:** http://127.0.0.1:5000/book
- **Ask the offline assistant:** http://127.0.0.1:5000/assistant
- **Doctor dashboard:** http://127.0.0.1:5000/dashboard (links to all of the above)

## How triage works (`analyze_symptoms`)

Keyword-based, offline, no external AI calls:

- **URGENT** — chest pain, difficulty breathing, severe bleeding, unconscious,
  seizure, stroke, severe allergic reaction.
- **URGENT (age-escalated)** — a patient aged 65+ with an otherwise
  MODERATE symptom (e.g. high fever) is escalated to URGENT.
- **MODERATE** — high fever, vomiting, dehydration, severe headache,
  persistent pain, dizziness.
- **NORMAL** — anything else.

This is decision support only — the UI explicitly notes that a healthcare
professional must confirm the final assessment.

## Appointment booking

Separate from patient registration, patients can book an appointment
(department, date, time) on the `/book` page. Like patient records, each
appointment is saved locally first (`synced = 0`) and pushed to the central
server by the same background sync loop.

## Offline FAQ assistant

The `/assistant` page lets a user ask basic hospital questions — services,
visiting hours, emergency care, departments, how to book — and gets an
answer from a small local knowledge base (`answer_question()` in `app.py`),
no internet or external AI service required. Unrecognized questions get a
polite fallback pointing to reception. This is intentionally simple keyword
matching, not a real NLP/LLM — see "Known limitations" below.

## Offline-first sync

- Every registration is saved locally immediately (`synced = 0`) — the app
  never blocks on network access.
- A background thread (`automatic_sync`) tries to push unsynced patients to
  the central server every 10 seconds.
- If the server is unreachable, the attempt fails silently and the record
  stays pending — nothing is lost, and it retries on the next cycle.
- You can also trigger a manual sync with `POST /sync`.

## API endpoints

| Method | Route              | Purpose                                   |
|--------|--------------------|--------------------------------------------|
| GET    | `/`                | Health check                               |
| GET    | `/dashboard`        | Doctor dashboard UI                        |
| GET    | `/register`         | Patient registration UI                    |
| POST   | `/register_patient` | Register a patient + run triage            |
| GET    | `/patients`          | List all patients (sorted by priority)     |
| GET    | `/book`              | Appointment booking page                   |
| POST   | `/book_appointment`   | Book an appointment                        |
| GET    | `/appointments`        | List all appointments                      |
| GET    | `/assistant`           | Offline FAQ assistant UI                   |
| POST   | `/ask`                 | Ask the offline FAQ assistant a question   |
| POST   | `/sync`              | Manually trigger a sync attempt            |

## Known limitations / next steps

- `server.py`'s `/sync_patient` endpoint has no authentication — anyone who
  can reach port 5001 can write patient records. Fine for a local demo/college
  project; would need an API key or network restriction for real use.
- Triage and the FAQ assistant are both keyword matching, not a real ML/NLP
  model — either can be fooled by phrasing they don't recognize (e.g.
  "can't breathe" vs "difficulty breathing"). Worth expanding the keyword
  lists, or swapping in a small local model, if you want to strengthen this
  for a demo.
- Flask's built-in dev server is used (`debug=True`) — fine for a project
  demo, not for production deployment.
