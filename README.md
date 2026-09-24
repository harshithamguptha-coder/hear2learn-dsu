# Accessible Classroom — MVP foundation

A small classroom app with a teacher lecture flow, a student join flow, and a
live transcript backed by SQLite. It intentionally contains no translation,
notes, Q&A, speaker detection, or other advanced AI features yet.

## What works

- A teacher can create a lecture with a unique session ID and end it.
- A student can validate and join that ID without an account.
- The teacher can turn on browser microphone capture.
- The Web Speech API converts speech to text through the browser.
- Finalized text is sent to FastAPI, saved in SQLite, and broadcast with SSE.
- Students receive the saved transcript first and then live additions.
- Reconnecting students receive the SQLite-backed transcript again.
- A session ID is a 64-bit random hexadecimal string. A database primary key
  prevents duplicates, and creation retries if a collision ever occurs.

## Project structure

```text
backend/
  app/
    api.py                  # HTTP and SSE routes
    database.py             # SQLite connection and schema
    models.py               # Request/response schemas
    services/
      session_service.py   # Session and transcript storage
      realtime.py           # In-memory live event queues
  tests/                    # API and SSE tests
frontend/
  src/
    api/client.js           # Small API client
    components/             # Shared transcript view
    hooks/                  # Speech recognition and SSE hooks
    pages/                  # Teacher and student pages
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

Open **http://localhost:5173** in a current Chrome or Edge browser. Visit
`/teacher` to start a lecture, then visit `/student` (in another tab or browser)
and enter the displayed session ID.

The Vite development server proxies `/api` to the backend, so the two processes
work on their default ports without extra configuration.

## Test and build

From `C:\Users\Harshitha\OneDrive\Desktop\dsu\backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From `C:\Users\Harshitha\OneDrive\Desktop\dsu\frontend`:

```powershell
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

## Data location

The default database is `backend/classroom.db`. To use another path, set
`DATABASE_PATH` before starting Uvicorn. Delete the `.db` file to reset all
local lecture and transcript data.

## API summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check backend health |
| `POST` | `/api/sessions` | Start a lecture |
| `GET` | `/api/sessions/{session_id}` | Validate/join a lecture |
| `POST` | `/api/sessions/{session_id}/end` | End a lecture |
| `GET` | `/api/sessions/{session_id}/transcript` | Read saved transcript |
| `POST` | `/api/sessions/{session_id}/transcript` | Save finalized text |
| `GET` | `/api/sessions/{session_id}/events` | Subscribe to live SSE events |
