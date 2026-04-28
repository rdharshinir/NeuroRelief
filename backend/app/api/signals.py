"""
Signals API – list/get fused need signals, trigger priority refresh
Supports both Firebase Firestore (cloud) and SQL backends with auto-failover.
"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db_manager import db_manager
from app.core.database import get_db, Signal
from app.core.algorithms import compute_priority_score
from app.models.schemas import SignalOut

router = APIRouter(prefix="/signals", tags=["Signals"])


# ═════════════════════════════════════════════
# FIREBASE handlers
# ═════════════════════════════════════════════

async def _list_signals_firebase(status_filter: str | None, limit: int) -> list[dict]:
    store = db_manager.get_firestore()
    return await store.list_signals(status=status_filter, limit=limit)


async def _get_signal_firebase(signal_id: str) -> dict:
    store = db_manager.get_firestore()
    sig = await store.get_signal(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    return sig


async def _refresh_priority_firebase(signal_id: str) -> dict:
    store = db_manager.get_firestore()
    sig = await store.get_signal(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    first_seen = sig.get("first_seen", datetime.now(timezone.utc))
    if isinstance(first_seen, str):
        first_seen = datetime.fromisoformat(first_seen)
    new_priority = compute_priority_score(sig["urgency_score"], first_seen)
    updated = await store.update_signal(signal_id, {"priority_score": new_priority})
    return updated


async def _update_status_firebase(signal_id: str, new_status: str) -> dict:
    store = db_manager.get_firestore()
    sig = await store.get_signal(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    updated = await store.update_signal(signal_id, {"status": new_status})
    return updated


# ═════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════

@router.get("/", response_model=list[SignalOut])
async def list_signals(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    List all fused signals. Optionally filter by status (open/assigned/resolved).
    Results ordered by priority_score descending (highest urgency first).
    """
    if db_manager.is_cloud:
        return await _list_signals_firebase(status, limit)

    try:
        query = select(Signal).order_by(Signal.priority_score.desc()).limit(limit)
        if status:
            query = query.where(Signal.status == status)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in list_signals: {e}")
        await db_manager.handle_sql_failure()
        return await _list_signals_firebase(status, limit)


@router.get("/{signal_id}", response_model=SignalOut)
async def get_signal(signal_id: UUID, db: AsyncSession = Depends(get_db)):
    if db_manager.is_cloud:
        return await _get_signal_firebase(str(signal_id))

    try:
        result = await db.execute(select(Signal).where(Signal.id == signal_id))
        sig = result.scalar_one_or_none()
        if not sig:
            raise HTTPException(status_code=404, detail="Signal not found")
        return sig
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in get_signal: {e}")
        await db_manager.handle_sql_failure()
        return await _get_signal_firebase(str(signal_id))


@router.post("/{signal_id}/refresh-priority", response_model=SignalOut)
async def refresh_priority(signal_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Recalculate priority_score for a signal (applies time decay).
    Call periodically (e.g. cron every 15 min) to keep rankings fresh.
    """
    if db_manager.is_cloud:
        return await _refresh_priority_firebase(str(signal_id))

    try:
        result = await db.execute(select(Signal).where(Signal.id == signal_id))
        sig = result.scalar_one_or_none()
        if not sig:
            raise HTTPException(status_code=404, detail="Signal not found")
        sig.priority_score = compute_priority_score(sig.urgency_score, sig.first_seen)
        sig.last_updated = datetime.now(timezone.utc)
        return sig
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in refresh_priority: {e}")
        await db_manager.handle_sql_failure()
        return await _refresh_priority_firebase(str(signal_id))


@router.patch("/{signal_id}/status", response_model=SignalOut)
async def update_signal_status(
    signal_id: UUID,
    new_status: str,
    db: AsyncSession = Depends(get_db),
):
    """Update signal status: open → assigned → resolved."""
    allowed = {"open", "assigned", "resolved"}
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")

    if db_manager.is_cloud:
        return await _update_status_firebase(str(signal_id), new_status)

    try:
        result = await db.execute(select(Signal).where(Signal.id == signal_id))
        sig = result.scalar_one_or_none()
        if not sig:
            raise HTTPException(status_code=404, detail="Signal not found")
        sig.status = new_status
        sig.last_updated = datetime.now(timezone.utc)
        return sig
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in update_signal_status: {e}")
        await db_manager.handle_sql_failure()
        return await _update_status_firebase(str(signal_id), new_status)
