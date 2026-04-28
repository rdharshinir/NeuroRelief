"""
Reports API – submit community reports, trigger signal fusion
Supports both Firebase Firestore (cloud) and SQL backends with auto-failover.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger("neurorelief.reports")

from app.core.db_manager import db_manager
from app.core.database import get_db, Report, Signal
from app.core.algorithms import (
    extract_severity,
    should_merge_reports,
    compute_new_centroid,
    compute_urgency_score,
    compute_priority_score,
)
from app.models.schemas import ReportCreate, ReportOut

router = APIRouter(prefix="/reports", tags=["Reports"])


# ═════════════════════════════════════════════
# FIREBASE FIRESTORE handlers
# ═════════════════════════════════════════════

async def _submit_report_firebase(payload: ReportCreate) -> dict:
    """Submit a report using Firebase Firestore backend."""
    store = db_manager.get_firestore()
    ts = payload.timestamp or datetime.now(timezone.utc)
    severity = extract_severity(payload.description, payload.issue_type)

    # Try to find a matching existing signal
    existing_signals = await store.list_open_signals_by_type(payload.issue_type)
    matched_signal = None
    for sig in existing_signals:
        sig_first_seen = sig.get("first_seen", ts)
        if isinstance(sig_first_seen, str):
            sig_first_seen = datetime.fromisoformat(sig_first_seen)
        if should_merge_reports(
            sig["center_lat"], sig["center_lon"], sig["issue_type"], sig_first_seen,
            payload.location_lat, payload.location_lon, payload.issue_type, ts,
        ):
            matched_signal = sig
            break

    # Merge or create signal
    if matched_signal:
        new_lat, new_lon = compute_new_centroid(
            matched_signal["center_lat"], matched_signal["center_lon"],
            matched_signal["report_count"],
            payload.location_lat, payload.location_lon,
        )
        new_count = matched_signal["report_count"] + 1
        new_severity = max(matched_signal["base_severity"], severity)
        new_urgency = compute_urgency_score(new_severity, new_count)
        sig_first_seen = matched_signal.get("first_seen", ts)
        if isinstance(sig_first_seen, str):
            sig_first_seen = datetime.fromisoformat(sig_first_seen)
        new_priority = compute_priority_score(new_urgency, sig_first_seen)

        await store.update_signal(matched_signal["id"], {
            "center_lat":    new_lat,
            "center_lon":    new_lon,
            "report_count":  new_count,
            "base_severity": new_severity,
            "urgency_score": new_urgency,
            "priority_score": new_priority,
        })
        signal_id = matched_signal["id"]
    else:
        urgency = compute_urgency_score(severity, 1)
        new_signal = await store.create_signal({
            "issue_type":     payload.issue_type,
            "center_lat":     payload.location_lat,
            "center_lon":     payload.location_lon,
            "report_count":   1,
            "base_severity":  float(severity),
            "urgency_score":  urgency,
            "priority_score": compute_priority_score(urgency, ts),
            "first_seen":     ts,
            "last_updated":   ts,
        })
        signal_id = new_signal["id"]

    # Create report record
    report = await store.create_report({
        "location_lat":  payload.location_lat,
        "location_lon":  payload.location_lon,
        "issue_type":    payload.issue_type,
        "description":   payload.description,
        "severity":      severity,
        "timestamp":     ts,
        "reporter_name": payload.reporter_name,
        "signal_id":     signal_id,
    })
    return report


async def _list_reports_firebase(skip: int, limit: int) -> list[dict]:
    store = db_manager.get_firestore()
    return await store.list_reports(skip=skip, limit=limit)


async def _get_report_firebase(report_id: str) -> dict:
    store = db_manager.get_firestore()
    report = await store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ═════════════════════════════════════════════
# SQL handlers (original logic, wrapped for failover)
# ═════════════════════════════════════════════

async def _submit_report_sql(payload: ReportCreate, db: AsyncSession) -> Report:
    """Original SQL-based report submission."""
    ts = payload.timestamp or datetime.now(timezone.utc)
    severity = extract_severity(payload.description, payload.issue_type)

    result = await db.execute(
        select(Signal).where(
            and_(Signal.issue_type == payload.issue_type, Signal.status == "open")
        )
    )
    existing_signals = result.scalars().all()

    matched_signal = None
    for sig in existing_signals:
        if should_merge_reports(
            sig.center_lat, sig.center_lon, sig.issue_type, sig.first_seen,
            payload.location_lat, payload.location_lon, payload.issue_type, ts,
        ):
            matched_signal = sig
            break

    if matched_signal:
        new_lat, new_lon = compute_new_centroid(
            matched_signal.center_lat, matched_signal.center_lon,
            matched_signal.report_count,
            payload.location_lat, payload.location_lon,
        )
        matched_signal.center_lat   = new_lat
        matched_signal.center_lon   = new_lon
        matched_signal.report_count += 1
        matched_signal.base_severity = max(matched_signal.base_severity, severity)
        matched_signal.urgency_score = compute_urgency_score(
            matched_signal.base_severity, matched_signal.report_count
        )
        matched_signal.priority_score = compute_priority_score(
            matched_signal.urgency_score, matched_signal.first_seen
        )
        matched_signal.last_updated = datetime.now(timezone.utc)
        signal_id = matched_signal.id
    else:
        urgency = compute_urgency_score(severity, 1)
        new_signal = Signal(
            issue_type     = payload.issue_type,
            center_lat     = payload.location_lat,
            center_lon     = payload.location_lon,
            report_count   = 1,
            base_severity  = float(severity),
            urgency_score  = urgency,
            priority_score = compute_priority_score(urgency, ts),
            first_seen     = ts,
            last_updated   = ts,
        )
        db.add(new_signal)
        await db.flush()
        await db.refresh(new_signal)
        signal_id = new_signal.id

    report = Report(
        location_lat  = payload.location_lat,
        location_lon  = payload.location_lon,
        issue_type    = payload.issue_type,
        description   = payload.description,
        severity      = severity,
        timestamp     = ts,
        reporter_name = payload.reporter_name,
        signal_id     = signal_id,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


# ═════════════════════════════════════════════
# ROUTES (auto-select backend)
# ═════════════════════════════════════════════

@router.post("/", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def submit_report(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
    """
    Submit a new community report.
    Automatically:
      1. Extracts severity using Gemma 4 AI (or keyword fallback)
      2. Tries to merge into an existing nearby signal (same type, 1km, 24h)
      3. Creates a new signal if no match found
    Uses Firebase Firestore (cloud) or SQL based on active backend.
    """
    if db_manager.is_cloud:
        return await _submit_report_firebase(payload)

    # SQL path with failover
    try:
        return await _submit_report_sql(payload, db)
    except Exception as e:
        logger.error(f"SQL failed in submit_report: {e}")
        await db_manager.handle_sql_failure()
        return await _submit_report_firebase(payload)


@router.get("/", response_model=list[ReportOut])
async def list_reports(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List recent reports (paginated)."""
    if db_manager.is_cloud:
        return await _list_reports_firebase(skip, limit)

    try:
        result = await db.execute(
            select(Report).order_by(Report.timestamp.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"SQL failed in list_reports: {e}")
        await db_manager.handle_sql_failure()
        return await _list_reports_firebase(skip, limit)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    if db_manager.is_cloud:
        return await _get_report_firebase(str(report_id))

    try:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL failed in get_report: {e}")
        await db_manager.handle_sql_failure()
        return await _get_report_firebase(str(report_id))
