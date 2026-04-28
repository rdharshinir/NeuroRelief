# NeuroRelief

A Bio-Inspired Volunteer Coordination Platform converting scattered community reports into fused "need signals" using corroboration weighting, ranking them dynamically, and matching volunteers using a geo-affinity 4-axis compatibility engine (skills, distance, language, trust score).

## Features

*   **Cloud-First Architecture**: Firebase Firestore as default storage with automatic SQL fallback if configured.
*   **Gemma 4 AI Severity Extraction**: AI-powered report triage using Google's Gemma 4 model, with keyword-based fallback.
*   **Signal Fusion**: Merges reports within 1km and 24 hours of the same issue type.
*   **Urgency & Priority**: Weights base severity with logarithmic corroboration count, then ranks with exponential time-decay.
*   **Geo-Affinity Matching Engine**: A 4-axis (35% skill, 25% distance, 20% language, 20% trust) algorithm to find the optimum responders.
*   **Auto-Failover**: If SQL database goes down, the system automatically switches to Firebase Firestore without downtime.
*   **Minimal Command Dashboard**: Modern UI showing live signals and optimal volunteers.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  React UI   │────▶│  FastAPI Backend  │────▶│  DatabaseManager  │
│  (Vite)     │     │  + Gemma 4 AI    │     │  (Failover Logic) │
└─────────────┘     └──────────────────┘     └────────┬──────────┘
                                                      │
                                         ┌────────────┼────────────┐
                                         ▼            ▼            │
                                   ┌──────────┐ ┌──────────┐      │
                                   │ Firebase │ │   SQL    │      │
                                   │Firestore │ │(SQLite/  │      │
                                   │ (Default)│ │PostgreSQL│      │
                                   └──────────┘ └──────────┘      │
                                                                   │
                                                   Auto-failover ──┘
```

## Requirements

*   Python 3.10+
*   Node.js 18+
*   Firebase Project (for cloud storage)
*   Google AI Studio API Key (for Gemma 4 severity extraction – optional)

## Setup

### 1. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/) and create a project.
2. Enable **Cloud Firestore** in the project.
3. Go to **Project Settings → Service Accounts → Generate New Private Key**.
4. Save the downloaded JSON file as `firebase-credentials.json` in the `backend/` directory.

### 2. Gemma 4 AI Setup (Optional)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and generate an API key.
2. Add the key to `backend/.env`:
   ```
   GEMINI_API_KEY=your-api-key-here
   ```
   > If not configured, the system will use keyword-based severity extraction as fallback.

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Configure storage mode in `backend/.env`:
```env
# Options: cloud (default), sql, auto
STORAGE_MODE=cloud

# Firebase credentials
FIREBASE_CREDENTIALS=firebase-credentials.json

# Gemma 4 AI (optional)
GEMINI_API_KEY=your-key-here
```

> Database tables are created automatically. With `STORAGE_MODE=cloud`, no SQL setup is needed.

Run the seeder to populate sample data:
```bash
python seed.py
```

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

### Storage Modes

| Mode    | Behaviour                                                    |
|---------|--------------------------------------------------------------|
| `cloud` | Firebase Firestore only (default, no SQL needed)             |
| `sql`   | SQL database only (legacy mode, fails over to cloud if down) |
| `auto`  | Tries SQL first, falls back to Firebase if unavailable       |

### Health Check

Visit `http://localhost:8000/health` to see active backend status:
```json
{
  "status": "healthy",
  "storage": {
    "storage_mode": "cloud",
    "active_backend": "firebase_firestore",
    "sql_available": false,
    "firebase_ready": true
  },
  "ai_model": "gemma-4-31b-it",
  "severity_engine": "gemma4_with_keyword_fallback"
}
```

### Cloud Deployment (Docker)

To deploy to production quickly (AWS, DigitalOcean, GCP):
```bash
docker-compose up --build -d
```
*   `frontend` will be accessible on port 80.
*   `backend` will be accessible on port 8000.
*   Firebase Firestore is used as the default cloud database.

To populate dummy data after bringing the stack up:
```bash
docker-compose exec backend python seed.py
```
