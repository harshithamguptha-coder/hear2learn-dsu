# Accessible Classroom — MVP foundation

A small classroom app with a teacher lecture flow, a student join flow, a
live transcript backed by SQLite, optional Kannada/Hindi/Telugu translation, fixed-
phrase sign representation, and automatic session-scoped lecture notes. It
intentionally contains no Q&A, speaker detection, or other advanced AI
features yet.

## What works

- Persistent Teacher and Student accounts are stored in SQLite with scrypt-hashed passwords.
- Teachers and students register, log in, and are redirected to role-specific dashboards.
- Authenticated Teacher lectures store their title, Teacher owner, and start/end times in the existing session record.
- A teacher can create a lecture with a unique session ID and end it.
- A student can validate and join that ID after logging in.
- The teacher can turn on browser microphone capture.
- The Web Speech API converts speech to text through the browser.
- Finalized text is sent to FastAPI, saved in SQLite, and broadcast with SSE.
- Students receive the saved transcript first and then live additions.
- Students can request optional Kannada, Hindi, or Telugu translations per segment.
- Fixed classroom phrases can show local sign-representation placeholders.
- Ending a lecture generates notes from only that session's transcript.
- The original English remains visible if translation is unavailable.
- Reconnecting students receive the SQLite-backed transcript again.
- A session ID is a 64-bit random hexadecimal string. A database primary key
  prevents duplicates, and creation retries if a collision ever occurs.

## Project structure

```text
backend/
  app/
    auth_api.py              # Register, login, and role protection
    api.py                  # Lecture, transcript, and SSE routes
    attendance_api.py       # Student join/leave and My Lectures routes
    translation_api.py      # Session-scoped translation endpoint
    notes_api.py            # Session-scoped lecture notes endpoint
    database.py             # SQLite connection and schema
    models.py               # Request/response schemas
    services/
      attendance_service.py # Student attendance and personal history queries
      auth_service.py      # Password hashing, users, and signed bearer tokens
      session_service.py   # Session and transcript storage
      notes_service.py     # Deterministic extractive notes generation
      translation_service.py # Replaceable external translation provider
      realtime.py           # In-memory live event queues
  tests/                    # API and SSE tests
frontend/
  public/signs/         # Local MVP sign placeholder illustrations
  src/
    api/                  # Small API client
    components/           # Shared transcript, translation, and sign UI
    services/             # Fixed sign-phrase registry and lecture history helpers
    hooks/                # Speech recognition and SSE hooks
    pages/                # Teacher and student pages
```

## Run the backend

Install **Python 3.10 or newer**, open PowerShell, and run:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at **http://127.0.0.1:8000** and interactive API docs at
**http://127.0.0.1:8000/docs**.

## Run the frontend

Install **Node.js 20 or newer**, open a second PowerShell, and run:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\frontend
npm install
npm run dev
```

Open **http://localhost:5173** in a current Chrome or Edge browser. Register or
log in first, then visit `/teacher` or `/student`. Teachers can start a lecture;
Students can join using the displayed session ID.

The Vite development server proxies `/api` to the backend, so the two processes
work on their default ports without extra configuration.

## Test and build

From `C:\Users\Harshitha\OneDrive\Desktop\dsu\backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From `C:\Users\Harshitha\OneDrive\Desktop\dsu\frontend`:

```powershell
npm test
npm run build
```

## Speech recognition notes

The MVP uses the browser's Web Speech API rather than uploading raw audio to
a speech model. Chromium normally performs recognition through a browser speech
service, so an internet connection and microphone permission are required. STT
support varies by browser and is not guaranteed on every device. `localhost` is
treated as a secure context by modern browsers; a hosted copy must use HTTPS.

Only finalized words are persisted. Temporary/interim words are shown to the
teacher but are not sent to the API. In-memory SSE queues notify open pages;
SQLite is the durable source of truth and is restored into each new stream.

## Translation notes

The MVP uses MyMemory's no-key HTTP translation API through a replaceable
`TranslationService`. Kannada, Hindi, and Telugu requests are made only when a
student selects that language, so English remains the default and no provider
calls are made for the Teacher page. The public translation provider requires
an internet connection and has usage/rate limits. Translation is not stored in
SQLite; the English transcript remains the durable source and can be translated
again later.

## Sign representation notes

The Student transcript checks each finalized English segment against the fixed
MVP registry in `frontend/src/services/signLanguage.js`. Only these phrases are
supported: "Good morning", "Open your book", "Pay attention", "Any questions?",
and "Thank you". A match shows one local placeholder SVG beneath the original
and optional translation. Unsupported or longer sentences are not represented.
The current `session_id` scopes the Student rendering; no new session or API is
created.

## Automatic lecture notes

The project has no existing LLM configuration, so the MVP uses a small
standard-library extractive notes service rather than adding a model dependency.
On the first End Lecture request, it reads transcripts using only the current
`session_id` and stores one notes row for that session. Notes include a title,
short summary, main topics, key points, and important terms. Transcripts below
20 words return a clear "more speech needed" state. Students already connected
receive a session-ended SSE event and load the notes without refreshing, while
the full translated and signed transcript remains below the notes card.

## Student lecture history

The Student dashboard keeps a personal attendance record in SQLite. Joining an
active lecture stores `student_id`, `session_id`, and `joined_at`; leaving or
ending the lecture fills `left_at`. The **My Lectures** card shows only the
logged-in Student's own lecture title, date, attendance duration, Teacher, and
status. Lecture identifiers remain the existing `session_id` values.

## Authentication notes

Accounts are stored in the default SQLite database at `backend/classroom.db`.
Passwords are hashed with Python's built-in `scrypt`; plaintext passwords are
never stored or returned. Login tokens are short-lived bearer tokens kept in
browser `localStorage`. For a stable login session across backend restarts,
set an environment variable before starting Uvicorn:

```powershell
$env:AUTH_SECRET = "replace-this-with-a-long-random-secret"
```

If `AUTH_SECRET` is not set, the development server generates a new secret at
startup, so existing login tokens are invalidated when the backend restarts.

## Data location

The default database is `backend/classroom.db`. To use another path, set
`DATABASE_PATH` before starting Uvicorn. Delete the `.db` file to reset all
local lecture and transcript data.

## API summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check backend health |
| `POST` | `/api/auth/register` | Create a persistent Teacher or Student account |
| `POST` | `/api/auth/login` | Log in and receive a bearer token |
| `GET` | `/api/auth/me` | Read the logged-in account |
| `POST` | `/api/lectures` | Create a Teacher-owned lecture |
| `POST` | `/api/sessions` | Start a backward-compatible foundation lecture |
| `GET` | `/api/sessions/{session_id}` | Validate/join a lecture |
| `POST` | `/api/sessions/{session_id}/end` | End a lecture |
| `POST` | `/api/sessions/{session_id}/attendance/join` | Record the logged-in Student's join |
| `POST` | `/api/sessions/{session_id}/attendance/leave` | Record the Student's leave |
| `GET` | `/api/my-lectures` | List only the logged-in Student's attended lectures |
| `GET` | `/api/sessions/{session_id}/transcript` | Read saved transcript |
| `POST` | `/api/sessions/{session_id}/transcript` | Save finalized text |
| `GET` | `/api/sessions/{session_id}/events` | Subscribe to live SSE events |
| `POST` | `/api/sessions/{session_id}/translations` | Translate one English segment |
| `GET` | `/api/sessions/{session_id}/notes` | Get notes for one ended session |
