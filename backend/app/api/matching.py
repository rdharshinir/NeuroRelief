"""
Matching API – run geo-affinity matching engine, create/list assignments
Supports both Firebase Firestore (cloud) and SQL backends with auto-failover.
"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db_manager import db_manager
from app.core.database import get_db, Signal, Volunteer, Assignment
from app.core.algorithms import rank_volunteers, haversine_km
from app.models.schemas import MatchResult, AssignmentOut

router = APIRouter(prefix="/match", tags=["Matching"])

# Skill requirements per issue type (simple rule-based mapping)
ISSUE_SKILL_MAP: dict[str, list[str]] = {
    "medical":   ["medical", "first_aid", "nursing", "doctor"],
    "food":      ["logistics", "cooking", "driving"],
    "shelter":   ["construction", "logistics", "driving"],
    "rescue":    ["rescue", "swimming", "climbing", "driving"],
    "counseling":["counseling", "psychology", "social_work"],
    "transport": ["driving", "logistics"],
}

ISSUE_LANG_MAP: dict[str, list[str]] = {}  # extend as needed

MAX_DIST_KM = 50.0


# ═════════════════════════════════════════════
# FIREBASE handlers
# ═════════════════════════════════════════════

async def _match_firebase(signal_id: str, top_n: int) -> list[dict]:
    """Run matching using Firebase Firestore data."""
    store = db_manager.get_firestore()

    sig = await store.get_signal(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Fetch available volunteers and filter by distance
    all_volunteers = await store.list_volunteers(available_only=True, limit=500)
    nearby_volunteers = []
    for v in all_volunteers:
        dist = haversine_km(
            sig["center_lat"], sig["center_lon"],
            v["location_lat"], v["location_lon"],
        )
        if dist <= MAX_DIST_KM:
            nearby_volunteers.append(v)

    if not nearby_volunteers:
        return []

    signal_dict = {
        "issue_type":      sig["issue_type"],
        "center_lat":      sig["center_lat"],
        "center_lon":      sig["center_lon"],
        "required_skills": ISSUE_SKILL_MAP.get(sig["issue_type"].lower(), []),
        "required_langs":  ISSUE_LANG_MAP.get(sig["issue_type"].lower(), []),
    }

    vol_list = [
        {
            "id":           v["id"],
            "name":         v.get("name", "Unknown"),
            "skills":       v.get("skills", []),
            "languages":    v.get("languages", []),
            "location_lat": v["location_lat"],
            "location_lon": v["location_lon"],
            "trust_score":  v.get("trust_score", 0.5),
            "is_available": v.get("is_available", True),
        }
        for v in nearby_volunteers
    ]

    return rank_volunteers(vol_list, signal_dict, top_n=top_n)


async def _assign_firebase(signal_id: str, top_n: int) -> list[dict]:
    """Run matching and persist assignments to Firebase."""
    matched = await _match_firebase(signal_id, top_n)
    if not matched:
        raise HTTPException(status_code=404, detail="No available volunteers found")

    store = db_manager.get_firestore()
    assignments = []
    for match in matched:
        assignment = await store.create_assignment({
            "signal_id":      signal_id,
            "volunteer_id":   str(match["volunteer_id"]),
            "match_score":    match["total"],
            "skill_score":    match["skill_score"],
            "distance_score": match["distance_score"],
            "language_score": match["language_score"],
            "trust_score":    match["trust_score"],
            "status":         "suggested",
        })
        assignments.append(assignment)

    # Update signal status
    await store.update_signal(signal_id, {
        "status": "assigned",
        "assigned_volunteer_id": str(matched[0]["volunteer_id"]),
    })

    return assignments


async def _list_assignments_firebase(limit: int) -> list[dict]:
    store = db_manager.get_firestore()
    return await store.list_assignments(limit=limit)


# ═════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════

@router.get("/{signal_id}", response_model=list[MatchResult])
async def match_volunteers_for_signal(
    signal_id: UUID,
    top_n: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the 4-axis geo-affinity matching engine for a specific signal.
    Returns top_n volunteer matches ranked by:
        match_score = (skill*0.35) + (distance*0.25) + (language*0.20) + (trust*0.20)
    """
    if db_manager.is_cloud:
        return await _match_firebase(str(signal_id), top_n)

    try:
        # Fetch signal
        sig_result = await db.execute(select(Signal).where(Signal.id == signal_id))
        signal = sig_result.scalar_one_or_none()
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        # Fetch available volunteers within 50km
        from sqlalchemy import func
        import math

        sig_lat_rad = math.radians(signal.center_lat)
        sig_lon_rad = math.radians(signal.center_lon)

        dist_expr = 6371.0 * func.acos(
            func.cos(sig_lat_rad) * func.cos(func.radians(Volunteer.location_lat)) *
            func.cos(func.radians(Volunteer.location_lon) - sig_lon_rad) +
            func.sin(sig_lat_rad) * func.sin(func.radians(Volunteer.location_lat))
        )

        vol_result = await db.execute(
            select(Volunteer)
            .where(Volunteer.is_available == True)
            .where(func.coalesce(dist_expr, 0) <= MAX_DIST_KM)
        )
        volunteers = vol_result.scalars().all()

        if not volunteers:
            return []

        signal_dict = {
            "issue_type":      signal.issue_type,
            "center_lat":      signal.center_lat,
            "center_lon":      signal.center_lon,
            "required_skills": ISSUE_SKILL_MAP.get(signal.issue_type.lower(), []),
            "required_langs":  ISSUE_LANG_MAP.get(signal.issue_type.lower(), []),
        }

        vol_list = [
            {
                "id":           v.id,
                "name":         v.name,
                "skills":       v.skills or [],
                "languages":    v.languages or [],
                "location_lat": v.location_lat,
                "location_lon": v.location_lon,
                "trust_score":  v.trust_score,
                "is_available": v.is_available,
            }
            for v in volunteers
        ]

        return rank_volunteers(vol_list, signal_dict, top_n=top_n)

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in match_volunteers: {e}")
        await db_manager.handle_sql_failure()
        return await _match_firebase(str(signal_id), top_n)


@router.post("/{signal_id}/assign", response_model=list[AssignmentOut], status_code=status.HTTP_201_CREATED)
async def assign_volunteers(
    signal_id: UUID,
    top_n: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """
    Run matching and persist top_n assignments to the database.
    Also marks the signal as 'assigned'.
    """
    if db_manager.is_cloud:
        return await _assign_firebase(str(signal_id), top_n)

    try:
        matched = await match_volunteers_for_signal(signal_id, top_n=top_n, db=db)
        if not matched:
            raise HTTPException(status_code=404, detail="No available volunteers found")

        assignments_created = []
        for match in matched:
            assignment = Assignment(
                signal_id      = signal_id,
                volunteer_id   = match["volunteer_id"],
                match_score    = match["total"],
                skill_score    = match["skill_score"],
                distance_score = match["distance_score"],
                language_score = match["language_score"],
                trust_score    = match["trust_score"],
                status         = "suggested",
            )
            db.add(assignment)
            assignments_created.append(assignment)

        sig_result = await db.execute(select(Signal).where(Signal.id == signal_id))
        signal = sig_result.scalar_one_or_none()
        if signal:
            signal.status = "assigned"
            signal.assigned_volunteer_id = UUID(str(matched[0]["volunteer_id"]))
            signal.last_updated = datetime.now(timezone.utc)

        await db.flush()
        return assignments_created

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in assign_volunteers: {e}")
        await db_manager.handle_sql_failure()
        return await _assign_firebase(str(signal_id), top_n)


@router.get("/assignments/all", response_model=list[AssignmentOut])
async def list_assignments(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all assignments ordered by creation time."""
    if db_manager.is_cloud:
        return await _list_assignments_firebase(limit)

    try:
        result = await db.execute(
            select(Assignment).order_by(Assignment.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        import logging
        logging.getLogger("neurorelief").error(f"SQL failed in list_assignments: {e}")
        await db_manager.handle_sql_failure()
        return await _list_assignments_firebase(limit)
