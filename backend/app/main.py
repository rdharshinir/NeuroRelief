"""
NeuroRelief – FastAPI Application Entry Point
Cloud-first architecture: Firebase Firestore (default) with SQL fallback.
AI-powered severity extraction via Gemma 4.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.db_manager import db_manager

# Configure production logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neurorelief")


# ─────────────────────────────────────────────
# Lifespan: initialise storage backend on startup
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup sequence:
      1. DatabaseManager selects backend (cloud/sql/auto)
      2. Cloud (Firebase Firestore) is the default
      3. SQL is used only when configured AND available
      4. If SQL fails at any point, auto-failover to Firebase
    """
    logger.info("=" * 60)
    logger.info("  NeuroRelief API – Starting Up")
    logger.info("=" * 60)
    await db_manager.initialise()
    status_info = db_manager.get_status()
    logger.info(f"  Storage Mode:   {status_info['storage_mode']}")
    logger.info(f"  Active Backend: {status_info['active_backend']}")
    logger.info(f"  SQL Available:  {status_info['sql_available']}")
    logger.info(f"  Firebase Ready: {status_info['firebase_ready']}")
    logger.info("=" * 60)
    yield


# ─────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────
app = FastAPI(
    title       = "NeuroRelief API",
    description = "Bio-Inspired Volunteer Coordination Platform – Cloud-First with Gemma 4 AI",
    version     = "2.0.0",
    lifespan    = lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled inner exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error occurred. Please try again later."},
    )

# Allow React dev server (port 5173) and any origin in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register routers ──────────────────────────
from app.api import reports, signals, volunteers, matching, dashboard

app.include_router(reports.router)
app.include_router(signals.router)
app.include_router(volunteers.router)
app.include_router(matching.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status":  "ok",
        "service": "NeuroRelief API v2.0",
        "backend": db_manager.active_backend.value,
        "ai_model": "gemma-4-31b-it",
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Extended health endpoint showing active storage backend,
    storage mode, and component availability.
    """
    status_info = db_manager.get_status()
    return {
        "status":         "healthy",
        "storage":        status_info,
        "ai_model":       "gemma-4-31b-it",
        "severity_engine": "gemma4_with_keyword_fallback",
    }
