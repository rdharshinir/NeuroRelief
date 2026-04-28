"""
NeuroRelief – Database Manager (Failover Controller)
Orchestrates storage backend selection:
  - Default: Firebase Firestore (cloud)
  - Fallback: SQLite/PostgreSQL (if configured and available)
  - Auto: Try SQL first → fallback to Firebase on failure
"""
import os
import logging
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# Ensure .env is loaded before module-level singleton creation
load_dotenv()

logger = logging.getLogger("neurorelief.db_manager")


class StorageMode(str, Enum):
    CLOUD = "cloud"     # Firebase Firestore only (default)
    SQL   = "sql"       # SQLAlchemy only (legacy)
    AUTO  = "auto"      # Try SQL → fallback to Firebase


class ActiveBackend(str, Enum):
    FIREBASE  = "firebase_firestore"
    SQL       = "sql_database"
    NONE      = "none"


class DatabaseManager:
    """
    Singleton that manages which storage backend is active.
    Cloud (Firebase) is the default; SQL is the fallback/option.
    """

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._mode = StorageMode(os.getenv("STORAGE_MODE", "cloud").lower())
        self._active_backend = ActiveBackend.NONE
        self._firestore_storage = None
        self._sql_available = False
        logger.info(f"DatabaseManager initialised with mode: {self._mode.value}")

    @property
    def mode(self) -> StorageMode:
        return self._mode

    @property
    def active_backend(self) -> ActiveBackend:
        return self._active_backend

    @property
    def is_cloud(self) -> bool:
        return self._active_backend == ActiveBackend.FIREBASE

    @property
    def is_sql(self) -> bool:
        return self._active_backend == ActiveBackend.SQL

    # ─────────────────────────────────────
    # Initialisation (called during app lifespan)
    # ─────────────────────────────────────
    async def initialise(self):
        """
        Initialise the appropriate backend based on STORAGE_MODE.
        Called once during FastAPI lifespan startup.
        """
        if self._mode == StorageMode.SQL:
            # SQL only – fail hard if SQL is unavailable
            sql_ok = await self._try_sql_init()
            if not sql_ok:
                logger.error("SQL mode selected but database is unavailable!")
                # Fallback to cloud even in SQL mode to keep app running
                logger.warning("Falling back to Firebase Firestore...")
                await self._init_firebase()
            return

        if self._mode == StorageMode.AUTO:
            # Try SQL first, fallback to Firebase
            sql_ok = await self._try_sql_init()
            if sql_ok:
                logger.info("AUTO mode: SQL database is available, using SQL backend")
                return
            logger.warning("AUTO mode: SQL unavailable, falling back to Firebase Firestore")
            await self._init_firebase()
            return

        # Default: CLOUD mode
        await self._init_firebase()

    async def _try_sql_init(self) -> bool:
        """Attempt to initialise and verify SQL connectivity."""
        try:
            from app.core.database import init_db, test_sql_connection
            connection_ok = await test_sql_connection()
            if connection_ok:
                await init_db()
                self._sql_available = True
                self._active_backend = ActiveBackend.SQL
                logger.info("SQL database connected and tables initialised")
                return True
            return False
        except Exception as e:
            logger.error(f"SQL initialisation failed: {e}")
            return False

    async def _init_firebase(self):
        """Initialise Firebase Firestore backend."""
        try:
            from app.core.cloud_storage import FirestoreStorage
            self._firestore_storage = FirestoreStorage()
            # Verify connectivity
            health_ok = await self._firestore_storage.health_check()
            if health_ok:
                self._active_backend = ActiveBackend.FIREBASE
                logger.info("Firebase Firestore backend active and healthy")
            else:
                # Even if health check fails, keep Firebase as backend
                # (might be first run with empty collections)
                self._active_backend = ActiveBackend.FIREBASE
                logger.warning("Firebase health check returned empty, but backend set to Firestore")
        except Exception as e:
            logger.error(f"Firebase initialisation failed: {e}")
            # Last resort: try SQL
            if not self._sql_available:
                logger.warning("Attempting SQL as last resort...")
                await self._try_sql_init()

    # ─────────────────────────────────────
    # Get storage instance
    # ─────────────────────────────────────
    def get_firestore(self):
        """Get the FirestoreStorage instance."""
        if self._firestore_storage is None:
            from app.core.cloud_storage import FirestoreStorage
            self._firestore_storage = FirestoreStorage()
        return self._firestore_storage

    # ─────────────────────────────────────
    # Runtime failover
    # ─────────────────────────────────────
    async def handle_sql_failure(self):
        """
        Called when an SQL operation fails at runtime.
        Switches to Firebase Firestore automatically.
        """
        if self._active_backend == ActiveBackend.FIREBASE:
            return  # Already on Firebase

        logger.error("SQL runtime failure detected! Switching to Firebase Firestore...")
        self._sql_available = False
        await self._init_firebase()

    # ─────────────────────────────────────
    # Health / Status
    # ─────────────────────────────────────
    def get_status(self) -> dict:
        """Return current backend status for /health endpoint."""
        return {
            "storage_mode":   self._mode.value,
            "active_backend": self._active_backend.value,
            "sql_available":  self._sql_available,
            "firebase_ready": self._firestore_storage is not None,
        }


# ─────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────
db_manager = DatabaseManager()
