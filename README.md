# Hear2Learn

Accessible Classroom is a real-time, role-based AI education platform for Teachers and Students. A Teacher creates a lecture, speaks naturally, and shares a session ID. Students join the same lecture and receive live captions without refreshing the page. Each Student can personalize the learning view with Simplified, Translation, or Sign Support content.

This repository contains a functional end-to-end MVP: real accounts, persisted lecture data, browser speech recognition, SQLite storage, Server-Sent Events (SSE), accessibility preferences, attendance history, lecture notes, and Teacher analytics.

## Product capabilities

### Teacher workspace

- Register and log in with the `teacher` role.
- Create a lecture with a title and optional subject/topic.
- Receive a unique uppercase hexadecimal `session_id`.
- Enable the browser microphone and see interim and finalized speech.
- See one real-time **LIVE CAPTIONS** section with previous segments and newest speech.
- Copy the session ID for Students.
- End a lecture and persist its `ENDED` status.
- Browse only the logged-in Teacher’s stored lectures.
- Open one selected lecture by its own `session_id`; its transcript, attendance, questions, topics, accessibility usage, and notes are not mixed with another lecture.
- View real lecture duration, attendance, question, topic, and accessibility aggregates.

### Student workspace

- Register and log in with the `student` role.
- Join an active lecture using its `session_id`.
- Receive the saved transcript snapshot first, then live transcript events.
- See one clear **LIVE CAPTIONS** section that automatically scrolls to the newest saved caption.
- Select a saved per-Student, per-session mode: `Standard`, `Simplified`, `Translation`, or `Sign Support`.
- Choose Kannada, Hindi, or Telugu when Translation mode is selected.
- Keep the original English transcript available when translation is unavailable.
- Use local fixed-phrase sign representations for supported classroom phrases.
- View AI concepts, technical terms, numbers, formulas, and Lecture Assistant responses grounded to the current lecture.
- Keep attendance and completed lectures in **My Lectures** after logout/login.

### System behavior

- Only finalized speech is persisted. Interim Teacher speech is displayed locally but is not saved.
- Temporary browser SpeechRecognition interruptions are non-fatal and trigger guarded reconnection.
- Manual speech input remains available if microphone recognition cannot continue.
- Previous lectures never appear as `LIVE` after their stored session status becomes `ended`.
- Transcript, notes, conversation, attendance, and accessibility records are scoped by `session_id`.
- The optional AI layer is not required for captions, attendance, preferences, history, or stored notes.

> The old Student **“Classroom tools” placard/card section** has been removed from the current UI. Students access the underlying features through **Personalize your view** and the selected-content sections. The Simplified, Translation, Sign Support, AI intelligence, Lecture Assistant, and Lecture Notes functionality remains available.

## Models and providers

| Capability | Provider/model | Role |
|---|---|---|
| Speech-to-text | Browser `SpeechRecognition` / `webkitSpeechRecognition` | Converts microphone speech in Chrome/Edge. Raw audio is not uploaded to this project’s backend. |
| AI lesson structure | Groq `openai/gpt-oss-20b` by default | Produces clean text, topics, key points, concepts, technical terms, numbers, formulas, definitions, examples, and review moments. |
| Lecture-grounded Q&A | Groq `openai/gpt-oss-20b` by default | Answers using the current session transcript and recent conversation history. |
| Local AI fallback | `HeuristicAIProvider` | Deterministic offline rule-based structuring and Q&A; it is not an LLM. |
| Translation | MyMemory HTTP API | Translates individual English segments to `kn`, `hi`, or `te`; it is not the Groq model. |
| Lecture notes | Python `NotesService` | Deterministic extractive notes from the current transcript; no LLM call. |
| Sign Support | Local fixed-phrase registry and SVG assets | Provides illustrative animations for a small set of supported phrases; it is not unrestricted sign-language translation. |

### Configurable AI providers

The backend supports these `AI_PROVIDER` values:

- `groq` — Groq’s OpenAI-compatible API.
- `openai` — OpenAI Chat Completions.
- `gemini` — Google Gemini `generateContent` API.
- `heuristic`, `local`, or `none` — deterministic local fallback.
- `auto` — select an available external provider, otherwise use the heuristic provider.

The default local configuration is:

```dotenv
AI_PROVIDER=groq
GROQ_API_KEY=replace_with_your_groq_key
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

Groq requests use:

```text
POST https://api.groq.com/openai/v1/chat/completions
Authorization: Bearer <GROQ_API_KEY>
response_format: {"type": "json_object"}
```

The model is configurable with `GROQ_MODEL`. The API key is read from `backend/.env`; it is never stored in SQLite or committed to Git.


## Quick start

### Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer
- Chrome or Edge for browser microphone recognition
- Internet access for browser speech recognition, Groq (when enabled), and MyMemory translation
- A working microphone for the live SpeechRecognition demo

### Clone the repository

```powershell
cd C:\Users\Harshitha
git clone https://github.com/harshithamguptha-coder/hear2learn-dsu.git
cd hear2learn-dsu
```

If the project is already downloaded, use:

```text
C:\Users\Harshitha\OneDrive\Desktop\dsu
```

### Start the backend

Open PowerShell window 1:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create the local environment file if needed:

```powershell
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}
notepad .env
```

Paste the Groq key after `GROQ_API_KEY=`. Do not add quotes and do not commit `.env`.

Optionally set a stable development authentication secret:

```powershell
$env:AUTH_SECRET = "replace-this-with-a-long-random-secret"
```

Verify Groq without printing the key:

```powershell
.\.venv\Scripts\python.exe verify_groq.py
```

Start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

### Start the frontend

Open PowerShell window 2:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Use `localhost` consistently. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

## Recommended judge demo

Use a normal browser profile for the Teacher and an Incognito/separate profile for the Student. Separate profiles are recommended because the login token is stored in browser `localStorage`.

### 1. Create accounts

Open:

```text
http://localhost:5173/register?role=teacher
http://localhost:5173/register?role=student
```

Example credentials:

```text
Teacher: teacher@example.com / StrongPass123!
Student: student@example.com / StrongPass123!
```

### 2. Teacher starts a lecture

1. Log in as the Teacher.
2. Open **Start New Lecture** from the sidebar.
3. Enter `Operating Systems` as the title and `Computer Science` as the optional topic.
4. Click **Start Lecture**.
5. Show the generated session ID.
6. Click **Enable microphone** and allow permission.
7. Say:

```text
Good morning. Today we are learning operating systems.
A process is a program that is currently running.
```

The Teacher sees interim speech immediately and finalized captions saved in the database. If microphone recognition is unavailable, use **Manual speech input**; it uses the same real transcript endpoint and SSE flow.

### 3. Student joins

1. In the Student profile, click **Join New Lecture**.
2. Paste the session ID.
3. Click **Join Lecture**.
4. Speak another sentence from the Teacher window:

```text
The operating system manages CPU, memory, and input devices.
```

The Student receives the same saved transcript through SSE without a refresh.

### 4. Show accessibility personalization

Use the **Personalize your view** dropdown:

- `Simplified` shows easier-language learning support.
- `Translation` shows Kannada, Hindi, or Telugu selection.
- `Sign Support` shows supported local phrase animations.

Each Student’s mode is stored using both `student_id` and `session_id`, so two classmates can choose different modes in the same lecture.

### 5. Show AI Classroom Intelligence

After enough transcript exists, show Groq-generated concepts, technical information, numbers, formulas, and Lecture Assistant Q&A.

Ask:

```text
What is a process?
```

The assistant is instructed to use only the current lecture transcript. If Groq is unavailable, the UI shows a small non-blocking fallback and the core classroom continues working.

### 6. End and verify persistence

1. Teacher clicks **End lecture**.
2. Teacher and Student views change to `ENDED`.
3. The saved transcript remains visible.
4. Teacher opens **Recent Lectures** and selects that lecture.
5. Student opens **My Lectures**, logs out, logs back in, and confirms the lecture remains.


## Architecture

### Live captions

```text
Teacher microphone
        ↓
Browser Web Speech API
        ↓
Finalized text
        ↓
POST /api/sessions/{session_id}/transcript
        ↓
SQLite transcript row
        ↓
EventHub publishes transcript event
        ↓
GET /api/sessions/{session_id}/events (SSE)
        ↓
Student TranscriptView
```

- The Teacher and Student each render one `TranscriptView`; there is no duplicate caption UI.
- New transcript rows have unique database IDs and are merged/sorted in the frontend.
- A Student receives a saved transcript snapshot before live events.
- SSE sends a reconnect hint, session-ended events, and periodic keep-alive comments.
- The browser’s `EventSource` reconnects automatically; a reconnecting Student can receive the SQLite snapshot again.
- SpeechRecognition uses one guarded recognition instance per Teacher page and one shared restart timer.
- The lecture is not ended because of a temporary speech network interruption.

### AI path

```text
Saved transcript for one session
        ↓
Groq OpenAI-compatible /chat/completions endpoint
        ↓
Structured concepts/terms/numbers/formulas
        ↓
Lecture-grounded Q&A and multi-turn conversation
```

### Accessibility path

```text
Student selects a mode
        ↓
Preference saved by (student_id, session_id)
        ↓
Simplified local view / MyMemory translation / local sign registry
```

## Data and session isolation

SQLite is the durable source of truth. Important tables are:

- `users` — accounts and roles.
- `sessions` — lecture/session ID, title, Teacher owner, status, and timestamps.
- `transcripts` — finalized transcript segments associated with one `session_id`.
- `lecture_notes` — one generated notes record per session.
- `lecture_attendance` — Student/session join and leave records.
- `student_accessibility_preferences` — one mode/language preference per Student/session pair.
- `conversations` and `conversation_messages` — session-scoped Lecture Assistant conversations.

Primary isolation rules:

- Teacher dashboards query `WHERE session.teacher_id = ?`.
- Student history queries `WHERE attendance.student_id = ?`.
- Accessibility preferences use the composite key `(student_id, session_id)`.
- Transcripts, notes, and conversations always use the selected `session_id`.
- A conversation ID from Lecture A cannot be used with Lecture B.
- A selected lecture detail never combines Lecture A and Lecture B data.

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/register` | Create a Teacher or Student account |
| `POST` | `/api/auth/login` | Authenticate and return a bearer token |
| `GET` | `/api/auth/me` | Read the current account |
| `POST` | `/api/lectures` | Create a Teacher-owned lecture |
| `POST` | `/api/sessions` | Backward-compatible foundation session creation |
| `GET` | `/api/sessions/{session_id}` | Validate/read a session |
| `POST` | `/api/sessions/{session_id}/end` | End a session and generate notes |
| `GET` | `/api/sessions/{session_id}/transcript` | Read saved transcript segments |
| `POST` | `/api/sessions/{session_id}/transcript` | Save finalized transcript text |
| `GET` | `/api/sessions/{session_id}/events` | Subscribe to transcript and ended events via SSE |
| `POST` | `/api/sessions/{session_id}/structure` | Structure the current transcript with the selected AI provider |
| `POST` | `/api/sessions/{session_id}/qa` | Answer a session-grounded question |
| `POST` | `/api/sessions/{session_id}/conversations` | Create a session-scoped conversation |
| `GET` | `/api/sessions/{session_id}/conversations/{conversation_id}` | Read a session-scoped conversation |
| `POST` | `/api/sessions/{session_id}/translations` | Translate one English segment |
| `GET` | `/api/sessions/{session_id}/notes` | Read notes for one ended session |
| `POST` | `/api/sessions/{session_id}/attendance/join` | Record Student attendance |
| `POST` | `/api/sessions/{session_id}/attendance/leave` | Record Student leave |
| `GET` | `/api/my-lectures` | List only the logged-in Student’s lectures |
| `GET` | `/api/sessions/{session_id}/accessibility` | Read the Student’s saved mode for one session |
| `POST` | `/api/sessions/{session_id}/accessibility` | Save the Student’s mode for one session |
| `GET` | `/api/teacher/dashboard` | Return the logged-in Teacher’s aggregates |

## Authentication and security

- Passwords are hashed with Python’s built-in `scrypt` using a random salt.
- Passwords are never returned by the API or stored in plaintext.
- Login responses contain a signed bearer token.
- Tokens contain a user ID, role, and expiration and use HMAC-SHA256 signatures.
- Tokens expire after eight hours.
- The frontend stores the token in `localStorage` for this local MVP.
- `.env` is ignored by Git; `.env.example` contains no real secret.
- CORS is configured for the local Vite origins.
- Teacher-only routes use `require_teacher`; Student attendance/accessibility/history routes use `require_student`.

### MVP security limitations

This is a local hackathon MVP, not a production security review. Before production deployment, add refresh-token rotation, stricter token storage, CSRF protection where relevant, rate limiting, secret management, HTTPS, audit logging, and authorization checks on every session-scoped route. Some legacy session/transcript foundation endpoints remain intentionally backward-compatible and are not all protected in the MVP.

## Translation, notes, and sign support

### Translation

`TranslationService` calls MyMemory’s no-key HTTP API for Kannada, Hindi, and Telugu. It chunks long text, validates script ranges, applies a small set of known classroom fallbacks, and caches up to 500 translations. Translations are not stored in SQLite; the English transcript remains the durable source and can be translated again.

### Lecture notes

`NotesService` is deterministic and standard-library based. It reads only the selected session transcript, ranks repeated meaningful terms and sentences, and stores one notes row per session. A transcript below 20 words produces a clear “more speech needed” state. Notes are not generated by Groq.

### Sign Support

The frontend uses a fixed local phrase registry and local animated/static SVG assets. The current MVP phrases are:

- `Good morning`
- `Open your book`
- `Pay attention`
- `Any questions?`
- `Thank you`

Unsupported or unrestricted sentences are not represented as sign translations. The original transcript always remains visible.

## Accessibility design

- Semantic headings, labels, landmarks, and status regions.
- Keyboard-visible focus states.
- Text labels in addition to icons and color.
- Strong contrast and readable font sizes.
- `aria-live` transcript updates and explicit LIVE/ENDED labels.
- Reduced-motion support.
- Responsive layouts and mobile sidebar behavior.
- Original English remains available alongside translated content.
- Sign Support is explicitly documented as fixed-phrase support, not unrestricted translation.

## Testing and validation

Backend:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\frontend
npm test
npm run build
```

The current validation completed successfully with:

- Backend: **71 tests passed**
- Frontend: **12 tests passed**
- Frontend production build: **passed**
- Groq model/key verification: **passed**
- Real Groq structured-inference smoke test: **passed**
- `git diff --check`: **passed**

The test suite forces the deterministic local provider where appropriate, so automated tests do not spend the real Groq quota.

## Troubleshooting

### `cd hear2learn-dsu\backend` fails

Use the actual checkout path:

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
```

### `No module named uvicorn`

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Backend is not responding

Check:

```text
http://127.0.0.1:8000/api/health
```

Make sure PowerShell window 1 is still running Uvicorn.

### Port already in use

```powershell
Get-NetTCPConnection -State Listen | Where-Object {
    $_.LocalPort -in 8000,5173
}
```

Use the already-running process or stop the old process before restarting.

### Microphone does not work

- Use current Chrome or Edge.
- Open `http://localhost:5173`, not a raw LAN IP.
- Allow microphone permission.
- Check that the microphone is not muted or used by another application.
- Use **Manual speech input** as a deterministic fallback; it still uses the real transcript/SSE backend path.

### Groq is unavailable

```powershell
cd C:\Users\Harshitha\OneDrive\Desktop\dsu\backend
.\.venv\Scripts\python.exe verify_groq.py
```

If the key is blank, the service falls back locally. Restart Uvicorn after changing `.env`.

### Translation is unavailable

Translation needs internet access and may be rate-limited by MyMemory. The original English transcript remains visible.

## Design decisions and honest limitations

- **SQLite** keeps setup simple and provides durable local persistence; production would likely use PostgreSQL.
- **SSE** is appropriate for one-way Teacher-to-Student updates; bidirectional collaboration would use WebSockets.
- **In-memory EventHub** is simple and session-scoped but process-local. Multiple server replicas would need Redis, NATS, or another shared event bus.
- **Browser Web Speech API** avoids storing raw audio, but recognition quality depends on browser, network, microphone, and browser speech service.
- **Groq** accelerates JSON generation and Q&A, but external AI calls have latency, quota, and availability considerations.
- **Prompt grounding** reduces hallucination by supplying only the current transcript and enforcing a response contract; it is not a mathematical guarantee that an external model can never err.
- **Sign Support** is a fixed educational prototype, not a complete sign-language translator.
- **Translation** is optional and external; English is always the source of truth.
- **Authentication** is suitable for a local MVP, not a full production identity system.
- The removed Student “Classroom tools” cards are intentionally not part of the current UI; students use **Personalize your view** and selected content.

## Judge elevator pitch

> Accessible Classroom is a live, accessible education platform. Teachers create a session and speak naturally. Browser speech recognition turns finalized speech into session-scoped captions, FastAPI stores them in SQLite, and SSE delivers them to Students in real time. Students can choose Simplified, Translation, or Sign Support views, with preferences saved independently for each account and lecture. Groq adds grounded lesson insights and a lecture-only Q&A assistant, while deterministic local fallbacks keep the core classroom working when external services fail. Attendance, lecture history, notes, analytics, and transcript data remain isolated by session and user.

## License and repository

This repository is the Accessible Classroom MVP. Add the appropriate license before public distribution if required.
