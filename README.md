# Live Janmashtami College Quiz Application

A high-performance, modular full-stack application designed for live college quiz competitions. Built with FastAPI, SQLModel, SQLite (development) / MySQL (production), secure JWT admin and student token authentication, native WebSocket synchronization, and zero-framework responsive frontends for both students and the quiz host.

---

## Key Features

- **Admin Control Panel (`/admin`)**: Single-screen live quiz control for the operator: start rounds, broadcast questions, end rounds, inspect Top 5 leaderboards, and manage questions.
- **Student Live Quiz Frontend (`/`)**: Mobile-first, responsive interface with instant question delivery, single-click answer submission, and independent round leaderboards.
- **Real-Time WebSocket Sync (`WS /api/ws/quiz?token=<token>`)**: Push broadcasting of question starts and round completions to connected students without browser refreshes.
- **Strict Answer Ownership & Anti-Cheat**: Student identity is derived exclusively from server-signed JWT tokens; response times are calculated authoritatively on the backend.
- **Database-Level Duplicate Protection**: Composite unique constraint `(round_id, student_id)` prevents double-answering.
- **Independent Fast-Response Leaderboards**: Fresh round ranking sorted by `response_time_ms ASC`, highlighting the Top 5 fastest correct entries. No cumulative scores.
- **Zero Answer Leaks & Hardened Privacy**: Public questions and WebSocket payloads omit `correct_option`; public leaderboards omit phone numbers and email addresses.

---

## Application Access URLs

- **Student Quiz Arena**: [http://localhost:8000/](http://localhost:8000/)
- **Admin Control Panel**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Live Event Operator Workflow

```text
Host opens /admin
      ↓
Login (admin / admin123)
      ↓
Select Question from Dropdown
      ↓
Click "⚡ START QUESTION"
      ↓
All connected students automatically see the question
      ↓
Students tap their answer (options lock immediately)
      ↓
Host clicks "🛑 END QUESTION" (with confirmation)
      ↓
Leaderboard opens automatically
      ↓
Top 5 Fastest Correct participants highlighted (Prizes distributed)
      ↓
Host selects next question & repeats
```

---

## Directory Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app factory, CORS, static routes (/ and /admin), lifespan
│   ├── core/
│   │   ├── config.py            # Settings (DB, Admin JWT, Student JWT)
│   │   ├── database.py          # SQLModel Engine, get_session dependency
│   │   ├── security.py          # Admin/Student JWT logic, get_current_admin, get_current_student
│   │   └── exceptions.py        # Custom API exceptions & error codes
│   ├── models/
│   │   ├── enums.py             # RoundStatus, OptionEnum
│   │   ├── student.py           # Student SQLModel (unique reg_no & email)
│   │   ├── question.py          # Question SQLModel
│   │   ├── quiz_round.py        # QuizRound SQLModel
│   │   └── answer.py            # Answer SQLModel with UniqueConstraint("round_id", "student_id")
│   ├── schemas/
│   │   ├── auth.py              # LoginRequest, TokenResponse, AdminResponse
│   │   ├── student.py           # StudentCreate, StudentResponse, StudentAuthResponse
│   │   ├── question.py          # QuestionCreate, QuestionResponse, PublicQuestionResponse
│   │   ├── quiz.py              # QuizRoundCreate, QuizRoundResponse, ActiveQuizStateResponse
│   │   ├── answer.py            # AnswerSubmit (extra="forbid"), AnswerResponse
│   │   └── leaderboard.py       # LeaderboardEntry, LeaderboardResponse
│   ├── realtime/
│   │   ├── connection_manager.py# Multi-socket tracking, resilient broadcast, dead-socket pruning
│   │   └── events.py            # Event schemas (quiz_state, question_started, round_ended)
│   ├── crud/
│   │   ├── students.py          # Idempotent student registration & lookups
│   │   ├── questions.py         # Question CRUD
│   │   ├── quiz.py              # Round lifecycle & active round management
│   │   └── answers.py           # Answer insertion & integrity error handling
│   ├── services/
│   │   ├── quiz_service.py      # Business logic: round transitions, answer grading, server timing
│   │   └── leaderboard_service.py # Round ranking (response_time_ms ASC), Top 5 prize flags
│   └── routes/
│       ├── auth.py              # /api/admin/auth/login, /api/admin/auth/me
│       ├── student.py           # /api/students/register, /api/students/me, /api/students (Admin)
│       ├── quiz.py              # /api/quiz/* (active state, authenticated answers, leaderboards)
│       ├── admin.py             # /api/admin/* (question & round management)
│       └── ws.py                # WS /api/ws/quiz?token=... (Authenticated student WebSocket)
├── frontend/
│   ├── index.html               # Student live quiz interface
│   ├── admin.html               # Admin Control Panel interface
│   ├── css/
│   │   ├── style.css            # Student mobile-first styles
│   │   └── admin.css            # Admin dashboard desktop-first styles
│   └── js/
│       ├── state.js             # Student reactive state store
│       ├── api.js               # Student REST client
│       ├── websocket.js         # Student WebSocket auto-reconnect client
│       ├── app.js               # Student UI coordinator
│       ├── admin-api.js         # Admin authenticated API client
│       └── admin.js             # Admin dashboard controller
├── tests/                       # 60 automated tests covering all features
└── requirements.txt
```

---

## Getting Started

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run the Application
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Run Automated Tests
```bash
source .venv/bin/activate
pytest -v
```
*(60/60 tests passing)*
