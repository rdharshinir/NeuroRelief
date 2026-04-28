<p align="center">
  <h1 align="center">🧠 NeuroRelief</h1>
  <p align="center">
    <strong>Bio-Inspired Volunteer Coordination Platform</strong><br/>
    AI-powered disaster relief signal fusion &amp; geo-affinity volunteer matching
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React" />
    <img src="https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase&logoColor=black" alt="Firebase" />
    <img src="https://img.shields.io/badge/AI-Gemma%204-4285F4?logo=google&logoColor=white" alt="Gemma 4" />
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  </p>
</p>

---

## Overview

NeuroRelief converts scattered community disaster reports into actionable **fused need signals** using corroboration weighting, ranks them dynamically with time-decay priority scoring, and matches the best available volunteers using a **4-axis geo-affinity compatibility engine** (skills, distance, language, trust score).

## Features

| Feature | Description |
|---------|-------------|
| **Signal Fusion Engine** | Merges reports within 1 km and 24 hours of the same issue type into unified need signals |
| **Gemma 4 AI Triage** | AI-powered severity extraction (1-5 scale) with keyword-based fallback |
| **Priority Ranking** | `urgency = severity × log(1 + report_count)` + exponential time-decay |
| **Geo-Affinity Matching** | 4-axis scoring: skill (35%) + distance (25%) + language (20%) + trust (20%) |
| **Cloud-First Architecture** | Firebase Firestore default with automatic SQL failover |
| **Auto-Failover** | If SQL goes down, seamless switch to Firebase without downtime |
| **Modern Dashboard** | React + Leaflet map UI with live signals, reports, and volunteer management |

## Architecture

```
┌─────────────────┐       ┌──────────────────────┐       ┌───────────────────┐
│   React + Vite  │──────▶│   FastAPI Backend     │──────▶│  DatabaseManager  │
│   Dashboard     │  API  │   + Gemma 4 AI        │       │  (Failover Logic) │
│   (Port 5173)   │       │   (Port 8000)         │       └────────┬──────────┘
└─────────────────┘       └──────────────────────┘                │
                                                     ┌────────────┼────────────┐
                                                     ▼                         ▼
                                               ┌──────────┐             ┌──────────┐
                                               │ Firebase │             │   SQL    │
                                               │Firestore │             │(SQLite/  │
                                               │ (Default)│             │PostgreSQL│
                                               └──────────┘             └──────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Frontend** | React 18, Vite, Leaflet, Lucide Icons |
| **Database** | Firebase Firestore (cloud) / SQLite (local dev) / PostgreSQL (Docker) |
| **AI** | Google Gemma 4 (31B) via GenAI SDK |
| **Deployment** | Docker, Docker Compose, Nginx |

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **Firebase Project** (for cloud storage mode)
- **Google AI Studio API Key** (optional — for Gemma 4 severity extraction)

## Quick Start

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd NeuroRelief
```

Copy the environment template and fill in your keys:
```bash
cp backend/.env.example backend/.env
```

### 2. Firebase Setup (for cloud mode)

1. Go to [Firebase Console](https://console.firebase.google.com/) and create a project
2. Enable **Cloud Firestore**
3. Go to **Project Settings → Service Accounts → Generate New Private Key**
4. Save the JSON file as `backend/firebase-credentials.json`

> **Note:** If using `STORAGE_MODE=sql`, Firebase setup is optional.

### 3. Gemma 4 AI Setup (optional)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and generate an API key
2. Add to `backend/.env`:
   ```
   GEMINI_API_KEY=your-api-key-here
   ```
> If not configured, the system uses keyword-based severity extraction as fallback.

### 4. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

Start the API server:
```bash
uvicorn app.main:app --reload --port 8000
```

Seed sample data (**with the server running** in another terminal):
```bash
python seed.py
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** for the dashboard.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_MODE` | `cloud` | Storage backend: `cloud`, `sql`, or `auto` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./neurorelief.db` | SQL database connection string |
| `FIREBASE_CREDENTIALS` | `firebase-credentials.json` | Path to Firebase service account JSON |
| `GEMINI_API_KEY` | _(empty)_ | Google AI Studio API key for Gemma 4 |
| `CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |

### Storage Modes

| Mode | Behaviour |
|------|-----------|
| `cloud` | Firebase Firestore only (default, no SQL needed) |
| `sql` | SQL database only (SQLite for local, PostgreSQL for Docker) |
| `auto` | Tries SQL first, falls back to Firebase if unavailable |

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health check with backend status |
| `POST` | `/reports/` | Submit a community report (auto-fuses into signals) |
| `GET` | `/reports/` | List reports (paginated) |
| `GET` | `/signals/` | List fused signals (sorted by priority) |
| `POST` | `/signals/{id}/refresh-priority` | Recalculate priority with time decay |
| `PATCH` | `/signals/{id}/status` | Update signal status (open/assigned/resolved) |
| `POST` | `/volunteers/` | Register a new volunteer |
| `GET` | `/volunteers/` | List volunteers |
| `PATCH` | `/volunteers/{id}/availability` | Toggle volunteer availability |
| `GET` | `/match/{signal_id}` | Run 4-axis matching for a signal |
| `POST` | `/match/{signal_id}/assign` | Match and persist assignments |
| `GET` | `/dashboard/` | Aggregated dashboard data |

Full interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

## Docker Deployment

### Build & Run

```bash
docker-compose up --build -d
```

This starts:
- **PostgreSQL** on port 5432
- **Backend** (FastAPI) on port 8000
- **Frontend** (Nginx) on port 80

### Seed Data in Docker

```bash
docker-compose exec backend python seed.py
```

### Environment Overrides

Pass environment variables to the backend service in `docker-compose.yml`:
```yaml
environment:
  - STORAGE_MODE=sql
  - GEMINI_API_KEY=your-key-here
  - CORS_ORIGINS=https://yourdomain.com
```

### Cloud Deployment

Deploy to any cloud provider (AWS, GCP, DigitalOcean) that supports Docker Compose:

```bash
# Build production images
docker-compose build

# Push to registry
docker tag neurorelief-backend your-registry/neurorelief-backend:latest
docker push your-registry/neurorelief-backend:latest

# Deploy
docker-compose -f docker-compose.yml up -d
```

## Project Structure

```
NeuroRelief/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── dashboard.py  # Aggregated stats endpoint
│   │   │   ├── matching.py   # 4-axis geo-affinity engine
│   │   │   ├── reports.py    # Report submission + signal fusion
│   │   │   ├── signals.py    # Signal management + priority refresh
│   │   │   └── volunteers.py # Volunteer registration + management
│   │   ├── core/             # Business logic & infrastructure
│   │   │   ├── algorithms.py # Signal fusion, priority, matching algorithms
│   │   │   ├── cloud_storage.py  # Firebase Firestore backend
│   │   │   ├── database.py   # SQLAlchemy models + session management
│   │   │   └── db_manager.py # Storage backend selection + failover
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic request/response schemas
│   │   └── main.py           # FastAPI app entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── seed.py               # Sample data generator
│   └── .env.example          # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Signals, Reports, Volunteers
│   │   ├── App.jsx           # Root component + routing
│   │   ├── main.jsx          # React entry point
│   │   └── index.css         # Global styles
│   ├── Dockerfile            # Multi-stage build (Node → Nginx)
│   ├── nginx.conf            # Production reverse proxy config
│   └── package.json
├── database/
│   └── schema.sql            # PostgreSQL schema (Docker init)
├── docker-compose.yml
└── README.md
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `httpx.ConnectError` when running `seed.py` | Start the backend server first (`uvicorn app.main:app --port 8000`), then run seed.py in a separate terminal |
| `DLL load failed: _rust` on Windows | The `cryptography` package has a broken DLL. Set `STORAGE_MODE=sql` in `.env` to bypass Firebase |
| `ModuleNotFoundError: pydantic_core` | Run `pip install --force-reinstall pydantic pydantic-core` |
| `UnicodeEncodeError` on Windows | The seed script uses ASCII-safe characters. If you see this, update to the latest `seed.py` |
| Firebase health check fails | Ensure `firebase-credentials.json` exists and is valid. Or switch to `STORAGE_MODE=sql` |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
