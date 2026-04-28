"""
Volunteers API – register/list volunteers
Supports both Firebase Firestore (cloud) and SQL backends with auto-failover.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db_manager import db_manager
from app.core.database import get_db, Volunteer
from app.models.schemas import VolunteerCreate, VolunteerOut

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])


# ═════════════════════════════════════════════
# FIREBASE handlers
# ═════════════════════════════════════════════

async def _register_volunteer_firebase(payload: VolunteerCreate) -> dict:
    store = db_manager.get_firestore()
    return await store.create_volunteer({
        "name":         payload.name,
        "email":        payload.email,
        "skills":       payload.skills,
        "languages":    payload.languages,
        "location_lat": payload.location_lat,
        "location_lon": payload.location_lon,
        "trust_score":  payload.trust_score,
        "is_available": payload.is_available,
    })


async def _list_volunteers_firebase(available_only: bool, limit: int) -> list[dict]:
    store = db_manager.get_firestore()
    return await store.list_volunteers(available_only=available_only, limit=limit)


async def _get_volunteer_firebase(volunteer_id: str) -> dict:
    store = db_manager.get_firestore()
    vol = await store.get_volunteer(volunteer_id)
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return vol


async def _toggle_availability_firebase(volunteer_id: str, is_available: bool) -> dict:
    store = db_manager.get_firestore()
    vol = await store.get_volunteer(volunteer_id)
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    updated = await store.update_volunteer(volunteer_id, {"is_available": is_available})
    return updated


# ═════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════

@router.post("/", response_model=VolunteerOut, status_code=status.HTTP_201_CREATED)
async def register_volunteer(payload: VolunteerCreate, db: AsyncSession = Depends(get_db)):
    """Register a new volunteer with skills, languages, location and trust score."""
    if db_manager.is_cloud:
        return await _register_volunteer_firebase(payload)

    try:
        vol = Volunteer(
            name         = payload.name,
            email        = payload.email,
            skills       = payload.skills,
            languages    = payload.languages,
            location_lat = payload.location_lat,
            location_lon = payload.location_lon,
            trust_score  = payload.trust_score,
            is_available = payload.is_available,
        )
        db.add(vol)
        await db.flush()
        await db.refresh(vol)
        return vol
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in register_volunteer: {e}")
        await db_manager.handle_sql_failure()
        return await _register_volunteer_firebase(payload)


@router.get("/", response_model=list[VolunteerOut])
async def list_volunteers(
    available_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all volunteers. Set available_only=true to show only free volunteers."""
    if db_manager.is_cloud:
        return await _list_volunteers_firebase(available_only, limit)

    try:
        query = select(Volunteer).order_by(Volunteer.trust_score.desc()).limit(limit)
        if available_only:
            query = query.where(Volunteer.is_available == True)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in list_volunteers: {e}")
        await db_manager.handle_sql_failure()
        return await _list_volunteers_firebase(available_only, limit)


@router.get("/{volunteer_id}", response_model=VolunteerOut)
async def get_volunteer(volunteer_id: UUID, db: AsyncSession = Depends(get_db)):
    if db_manager.is_cloud:
        return await _get_volunteer_firebase(str(volunteer_id))

    try:
        result = await db.execute(select(Volunteer).where(Volunteer.id == volunteer_id))
        vol = result.scalar_one_or_none()
        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer not found")
        return vol
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in get_volunteer: {e}")
        await db_manager.handle_sql_failure()
        return await _get_volunteer_firebase(str(volunteer_id))


@router.patch("/{volunteer_id}/availability", response_model=VolunteerOut)
async def toggle_availability(
    volunteer_id: UUID,
    is_available: bool,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a volunteer's availability status."""
    if db_manager.is_cloud:
        return await _toggle_availability_firebase(str(volunteer_id), is_available)

    try:
        result = await db.execute(select(Volunteer).where(Volunteer.id == volunteer_id))
        vol = result.scalar_one_or_none()
        if not vol:
            raise HTTPException(status_code=404, detail="Volunteer not found")
        vol.is_available = is_available
        return vol
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in toggle_availability: {e}")
        await db_manager.handle_sql_failure()
        return await _toggle_availability_firebase(str(volunteer_id), is_available)
