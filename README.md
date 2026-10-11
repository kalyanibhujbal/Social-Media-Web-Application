# OpenVibe — AI-Assisted Social Media Content Moderation Prototype

A final-year B.E. Computer Engineering prototype for social-media text moderation. It has not been independently validated or certified for privacy, accessibility, or legal compliance.

---

## 🌟 Key Features & Core Modules

1. **User Input Module**: Interactive text submission for social media posts and comments.
2. **Text Preprocessing Module**: Normalization, whitespace cleaning, URL stripping, and tokenization.
3. **Language Identification**: Script and word-pattern heuristics identify some language labels; this does not make the inference model multilingual.
4. **Moderation Prediction**: English keyword rules and an optional locally cached English sentiment model are mapped to **Hate Speech**, **Offensive**, or **Normal** labels. This is not a validated hate-speech classifier.
5. **Rule Highlights**: Matching words are shown as keyword-rule indicators, not LIME/SHAP explanations or causal feature attributions.
6. **Content Moderation Module**: Policy decision engine mapping model predictions to moderation actions (`APPROVED`, `FLAGGED_FOR_REVIEW`, `BLOCKED`) with low-confidence routing for human review.
7. **Dashboard Module**: User-specific posts, comments, moderation state, and review history.
8. **Admin Module**: Backend-authorized content review, database-backed summaries, privacy request queue, and audit records.

---

## 🏗️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, PyTorch, Hugging Face Transformers, Pydantic, PyJWT.
- **Frontend**: React (Vite), keyboard focus styles, semantic landmarks, labeled forms, Context API.
- **Database**: MongoDB (via `motor`) is required in production; in-memory storage is for development only.
- **Testing**: Python `unittest` suite for preprocessing, classification, rule highlights, moderation policies, privacy workflows, and authorization.

---

## 📁 Repository Structure

```
Social Media/
├── backend/
│   ├── app/
│   │   ├── api/             # REST Endpoints (Auth, Posts, Moderation, Admin, Privacy)
│   │   ├── core/            # Config, Security (JWT/Password Hashing), Database
│   │   ├── models/          # Data Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   └── services/        # Preprocessing, LangDetect, Inference, XAI, Moderation Engine
│   ├── tests/               # Unit Test Suite
│   ├── .env.example         # Environment Variable Template
│   └── main.py              # FastAPI Application Entrypoint
├── frontend/
│   ├── src/
│   │   ├── components/      # Common, Post, Moderation, and Admin Components
│   │   ├── context/         # Auth & Cookie Consent Context Providers
│   │   ├── pages/           # Home, Login, Register, Dashboard, Admin, Legal Pages
│   │   ├── services/        # API Client Helper
│   │   ├── index.css        # Accessible Design System
│   │   └── App.jsx          # React Main Component
│   └── package.json
└── docs/
    ├── ARCHITECTURE.md      # Architecture & System Diagrams
    ├── DATABASE_SCHEMA.md   # MongoDB Collections & Indexes
    ├── API_CONTRACT.md      # REST API Specification
    ├── FRONTEND_ROUTES.md   # Frontend Route Mapping
    ├── MODEL_DOCUMENTATION.md # Transformer & Responsible AI Details
    ├── ACCESSIBILITY_CHECKLIST.md # Practices and unverified accessibility checks
    └── PRIVACY_DATA_MAP.md     # Actual data, access, storage, retention, and providers
```

---

## 🚀 Quick Start & How to Run

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Copy environment variables
cp .env.example .env

# Run unit tests
python -m unittest discover -s tests

# Start FastAPI server
python -m uvicorn main:app --reload --port 8000
```
Backend server starts at: `http://localhost:8000` (API Docs at `http://localhost:8000/docs`).

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build or start dev server
npm run dev
```
Frontend application runs at: `http://localhost:5173`.

---

## 🛡️ Administrator Setup

The application does not create a demo administrator or demo moderation data. For a deliberate bootstrap, set unique `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` values in the backend environment before the first startup. Browser logins use an HttpOnly session cookie; bearer tokens remain supported for API clients.

---

## Privacy and project notices

- The app does not use user content for model training. Optional analytics and tracking are not currently active.
- No paid products or payment transactions are implemented.
- Privacy, retention, security, accessibility practices, and limitations are documented in the in-app notices and [data map](docs/PRIVACY_DATA_MAP.md). No compliance certification is claimed.
- Configure verified operator and contact details in the backend environment before public deployment; the current placeholders are not an actual contact route.
