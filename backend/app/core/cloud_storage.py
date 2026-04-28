"""
NeuroRelief – Firebase Firestore Cloud Storage Backend
Provides async CRUD operations for all entities using Google Cloud Firestore.
Default storage backend; SQL is used only when explicitly configured and available.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("neurorelief.cloud")

# ─────────────────────────────────────────────
# Firestore Async Client (lazy init)
# ─────────────────────────────────────────────
_firestore_client = None


def _get_firestore_client():
    """Lazy-initialise Firebase Admin + Firestore AsyncClient."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    import firebase_admin
    from firebase_admin import credentials
    from google.cloud import firestore

    # Check if Firebase is already initialised
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialised from credentials file: {cred_path}")
        else:
            # Try Application Default Credentials (ADC)
            firebase_admin.initialize_app()
            logger.info("Firebase initialised with Application Default Credentials")

    _firestore_client = firestore.AsyncClient()
    logger.info("Firestore AsyncClient created successfully")
    return _firestore_client


# ─────────────────────────────────────────────
# Collection names
# ─────────────────────────────────────────────
COLLECTION_SIGNALS     = "signals"
COLLECTION_REPORTS     = "reports"
COLLECTION_VOLUNTEERS  = "volunteers"
COLLECTION_ASSIGNMENTS = "assignments"


# ─────────────────────────────────────────────
# Helper: convert Firestore doc → dict
# ─────────────────────────────────────────────
def _doc_to_dict(doc) -> Optional[dict]:
    """Convert a Firestore document snapshot to a dict with 'id' field."""
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def _ensure_uuid(val) -> str:
    """Ensure a value is a string UUID."""
    if val is None:
        return str(uuid.uuid4())
    return str(val)


def _ensure_datetime(val) -> datetime:
    """Ensure a value is a timezone-aware datetime."""
    if val is None:
        return datetime.now(timezone.utc)
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return val


# ═════════════════════════════════════════════
# FIRESTORE STORAGE CLASS
# ═════════════════════════════════════════════
class FirestoreStorage:
    """
    Async Firestore-backed storage for NeuroRelief.
    Drop-in replacement for SQLAlchemy session-based queries.
    """

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = _get_firestore_client()
        return self._db

    # ─────────────────────────────────────
    # SIGNALS
    # ─────────────────────────────────────
    async def create_signal(self, data: dict) -> dict:
        doc_id = _ensure_uuid(data.get("id"))
        now = datetime.now(timezone.utc)
        doc_data = {
            "issue_type":            data.get("issue_type", ""),
            "center_lat":            float(data.get("center_lat", 0)),
            "center_lon":            float(data.get("center_lon", 0)),
            "report_count":          int(data.get("report_count", 1)),
            "base_severity":         float(data.get("base_severity", 1.0)),
            "urgency_score":         float(data.get("urgency_score", 0.0)),
            "priority_score":        float(data.get("priority_score", 0.0)),
            "status":                data.get("status", "open"),
            "first_seen":            _ensure_datetime(data.get("first_seen", now)),
            "last_updated":          _ensure_datetime(data.get("last_updated", now)),
            "assigned_volunteer_id": data.get("assigned_volunteer_id"),
        }
        await self.db.collection(COLLECTION_SIGNALS).document(doc_id).set(doc_data)
        doc_data["id"] = doc_id
        return doc_data

    async def get_signal(self, signal_id: str) -> Optional[dict]:
        doc = await self.db.collection(COLLECTION_SIGNALS).document(str(signal_id)).get()
        return _doc_to_dict(doc)

    async def list_signals(self, status: Optional[str] = None, limit: int = 50) -> list[dict]:
        query = self.db.collection(COLLECTION_SIGNALS)
        if status:
            query = query.where("status", "==", status)
        query = query.order_by("priority_score", direction="DESCENDING").limit(limit)
        docs = await query.get()
        return [_doc_to_dict(doc) for doc in docs if doc.exists]

    async def list_signals_by_statuses(self, statuses: list[str], limit: int = 10) -> list[dict]:
        """List signals matching any of the given statuses, ordered by priority."""
        results = []
        for status_val in statuses:
            query = (
                self.db.collection(COLLECTION_SIGNALS)
                .where("status", "==", status_val)
                .order_by("priority_score", direction="DESCENDING")
                .limit(limit)
            )
            docs = await query.get()
            results.extend([_doc_to_dict(doc) for doc in docs if doc.exists])
        # Sort combined results by priority_score descending
        results.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return results[:limit]

    async def update_signal(self, signal_id: str, updates: dict) -> Optional[dict]:
        doc_ref = self.db.collection(COLLECTION_SIGNALS).document(str(signal_id))
        updates["last_updated"] = datetime.now(timezone.utc)
        await doc_ref.update(updates)
        doc = await doc_ref.get()
        return _doc_to_dict(doc)

    async def list_open_signals_by_type(self, issue_type: str) -> list[dict]:
        """List open signals filtered by issue type."""
        query = (
            self.db.collection(COLLECTION_SIGNALS)
            .where("issue_type", "==", issue_type)
            .where("status", "==", "open")
        )
        docs = await query.get()
        return [_doc_to_dict(doc) for doc in docs if doc.exists]

    async def count_signals_by_status(self, status: str) -> int:
        query = self.db.collection(COLLECTION_SIGNALS).where("status", "==", status)
        docs = await query.get()
        return len(docs)

    # ─────────────────────────────────────
    # REPORTS
    # ─────────────────────────────────────
    async def create_report(self, data: dict) -> dict:
        doc_id = _ensure_uuid(data.get("id"))
        now = datetime.now(timezone.utc)
        doc_data = {
            "location_lat":  float(data.get("location_lat", 0)),
            "location_lon":  float(data.get("location_lon", 0)),
            "issue_type":    data.get("issue_type", ""),
            "description":   data.get("description", ""),
            "severity":      int(data.get("severity", 1)),
            "timestamp":     _ensure_datetime(data.get("timestamp", now)),
            "signal_id":     data.get("signal_id"),
            "reporter_name": data.get("reporter_name"),
            "created_at":    _ensure_datetime(data.get("created_at", now)),
        }
        await self.db.collection(COLLECTION_REPORTS).document(doc_id).set(doc_data)
        doc_data["id"] = doc_id
        return doc_data

    async def get_report(self, report_id: str) -> Optional[dict]:
        doc = await self.db.collection(COLLECTION_REPORTS).document(str(report_id)).get()
        return _doc_to_dict(doc)

    async def list_reports(self, skip: int = 0, limit: int = 50) -> list[dict]:
        query = (
            self.db.collection(COLLECTION_REPORTS)
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit + skip)
        )
        docs = await query.get()
        all_docs = [_doc_to_dict(doc) for doc in docs if doc.exists]
        return all_docs[skip:]

    async def count_reports_since(self, since: datetime) -> int:
        query = self.db.collection(COLLECTION_REPORTS).where("created_at", ">=", since)
        docs = await query.get()
        return len(docs)

    # ─────────────────────────────────────
    # VOLUNTEERS
    # ─────────────────────────────────────
    async def create_volunteer(self, data: dict) -> dict:
        doc_id = _ensure_uuid(data.get("id"))
        now = datetime.now(timezone.utc)
        doc_data = {
            "name":         data.get("name", ""),
            "email":        data.get("email"),
            "skills":       data.get("skills", []),
            "languages":    data.get("languages", []),
            "location_lat": float(data.get("location_lat", 0)),
            "location_lon": float(data.get("location_lon", 0)),
            "trust_score":  float(data.get("trust_score", 0.5)),
            "is_available": data.get("is_available", True),
            "created_at":   _ensure_datetime(data.get("created_at", now)),
        }
        await self.db.collection(COLLECTION_VOLUNTEERS).document(doc_id).set(doc_data)
        doc_data["id"] = doc_id
        return doc_data

    async def get_volunteer(self, volunteer_id: str) -> Optional[dict]:
        doc = await self.db.collection(COLLECTION_VOLUNTEERS).document(str(volunteer_id)).get()
        return _doc_to_dict(doc)

    async def list_volunteers(self, available_only: bool = False, limit: int = 100) -> list[dict]:
        query = self.db.collection(COLLECTION_VOLUNTEERS)
        if available_only:
            query = query.where("is_available", "==", True)
        query = query.order_by("trust_score", direction="DESCENDING").limit(limit)
        docs = await query.get()
        return [_doc_to_dict(doc) for doc in docs if doc.exists]

    async def update_volunteer(self, volunteer_id: str, updates: dict) -> Optional[dict]:
        doc_ref = self.db.collection(COLLECTION_VOLUNTEERS).document(str(volunteer_id))
        await doc_ref.update(updates)
        doc = await doc_ref.get()
        return _doc_to_dict(doc)

    async def count_volunteers(self) -> int:
        docs = await self.db.collection(COLLECTION_VOLUNTEERS).get()
        return len(docs)

    # ─────────────────────────────────────
    # ASSIGNMENTS
    # ─────────────────────────────────────
    async def create_assignment(self, data: dict) -> dict:
        doc_id = _ensure_uuid(data.get("id"))
        now = datetime.now(timezone.utc)
        doc_data = {
            "signal_id":      data.get("signal_id"),
            "volunteer_id":   data.get("volunteer_id"),
            "match_score":    float(data.get("match_score", 0.0)),
            "skill_score":    float(data.get("skill_score", 0.0)),
            "distance_score": float(data.get("distance_score", 0.0)),
            "language_score": float(data.get("language_score", 0.0)),
            "trust_score":    float(data.get("trust_score", 0.0)),
            "status":         data.get("status", "suggested"),
            "created_at":     _ensure_datetime(data.get("created_at", now)),
        }
        await self.db.collection(COLLECTION_ASSIGNMENTS).document(doc_id).set(doc_data)
        doc_data["id"] = doc_id
        return doc_data

    async def list_assignments(self, limit: int = 100) -> list[dict]:
        query = (
            self.db.collection(COLLECTION_ASSIGNMENTS)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        docs = await query.get()
        return [_doc_to_dict(doc) for doc in docs if doc.exists]

    # ─────────────────────────────────────
    # HEALTH CHECK
    # ─────────────────────────────────────
    async def health_check(self) -> bool:
        """Verify Firestore connectivity by performing a lightweight read."""
        try:
            # Try to list 1 doc from any collection
            docs = await self.db.collection(COLLECTION_SIGNALS).limit(1).get()
            return True
        except Exception as e:
            logger.error(f"Firestore health check failed: {e}")
            return False
