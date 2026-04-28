"""
Dashboard API – aggregated stats for the frontend
Supports both Firebase Firestore (cloud) and SQL backends with auto-failover.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("neurorelief.dashboard")

from app.core.db_manager import db_manager
from app.core.database import get_db, Signal, Volunteer, Report, Assignment
from app.core.algorithms import rank_volunteers
from app.models.schemas import DashboardResponse, DashboardSignal, MatchResult
from app.api.matching import ISSUE_SKILL_MAP, ISSUE_LANG_MAP

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ═════════════════════════════════════════════
# FIREBASE handler
# ═════════════════════════════════════════════

async def _get_dashboard_firebase() -> dict:
    """Build dashboard data from Firebase Firestore."""
    store = db_manager.get_firestore()

    # Stats
    total_open = await store.count_signals_by_status("open")
    total_volunteers = await store.count_volunteers()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_reports_today = await store.count_reports_since(today_start)

    # Top signals (open + assigned)
    top_signals = await store.list_signals_by_statuses(["open", "assigned"], limit=10)

    # Fetch available volunteers
    all_volunteers = await store.list_volunteers(available_only=True, limit=500)
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
        for v in all_volunteers
    ]

    # Build dashboard signals with volunteer matches
    dashboard_signals = []
    for sig in top_signals:
        signal_dict = {
            "issue_type":      sig["issue_type"],
            "center_lat":      sig["center_lat"],
            "center_lon":      sig["center_lon"],
            "required_skills": ISSUE_SKILL_MAP.get(sig["issue_type"].lower(), []),
            "required_langs":  ISSUE_LANG_MAP.get(sig["issue_type"].lower(), []),
        }
        top_vols = rank_volunteers(vol_list, signal_dict, top_n=3)

        dashboard_signals.append(
            DashboardSignal(
                id             = sig["id"],
                issue_type     = sig["issue_type"],
                center_lat     = sig["center_lat"],
                center_lon     = sig["center_lon"],
                report_count   = sig["report_count"],
                priority_score = sig["priority_score"],
                urgency_score  = sig["urgency_score"],
                status         = sig["status"],
                top_volunteers = [
                    MatchResult(
                        volunteer_id   = m["volunteer_id"],
                        volunteer_name = m["volunteer_name"],
                        total          = m["total"],
                        skill_score    = m["skill_score"],
                        distance_score = m["distance_score"],
                        language_score = m["language_score"],
                        trust_score    = m["trust_score"],
                    )
                    for m in top_vols
                ],
            )
        )

    return DashboardResponse(
        total_open_signals  = total_open,
        total_volunteers    = total_volunteers,
        total_reports_today = total_reports_today,
        top_signals         = dashboard_signals,
    )


# ═════════════════════════════════════════════
# ROUTE
# ═════════════════════════════════════════════

@router.get("/", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated dashboard data:
    - Total open signals
    - Total volunteers
    - Reports submitted today
    - Top 10 prioritised open signals with top-3 volunteer matches each
    """
    if db_manager.is_cloud:
        return await _get_dashboard_firebase()

    try:
        # ── Stats ─────────────────────────────────────────────────────────────
        open_count_result = await db.execute(
            select(func.count(Signal.id)).where(Signal.status == "open")
        )
        total_open = open_count_result.scalar() or 0

        vol_count_result = await db.execute(select(func.count(Volunteer.id)))
        total_volunteers = vol_count_result.scalar() or 0

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        report_today_result = await db.execute(
            select(func.count(Report.id)).where(Report.created_at >= today_start)
        )
        total_reports_today = report_today_result.scalar() or 0

        # ── Top signals (open, by priority desc) ─────────────────────────────
        sig_result = await db.execute(
            select(Signal)
            .where(Signal.status.in_(["open", "assigned"]))
            .order_by(Signal.priority_score.desc())
            .limit(10)
        )
        top_signals = sig_result.scalars().all()

        # ── Fetch all available volunteers once (reuse for all signals) ────────
        vol_result = await db.execute(
            select(Volunteer).where(Volunteer.is_available == True)
        )
        all_volunteers = vol_result.scalars().all()
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
            for v in all_volunteers
        ]

        # ── Build dashboard signal list with volunteer matches ──────────────────
        dashboard_signals = []
        for sig in top_signals:
            signal_dict = {
                "issue_type":      sig.issue_type,
                "center_lat":      sig.center_lat,
                "center_lon":      sig.center_lon,
                "required_skills": ISSUE_SKILL_MAP.get(sig.issue_type.lower(), []),
                "required_langs":  ISSUE_LANG_MAP.get(sig.issue_type.lower(), []),
            }
            top_vols = rank_volunteers(vol_list, signal_dict, top_n=3)

            dashboard_signals.append(
                DashboardSignal(
                    id             = sig.id,
                    issue_type     = sig.issue_type,
                    center_lat     = sig.center_lat,
                    center_lon     = sig.center_lon,
                    report_count   = sig.report_count,
                    priority_score = sig.priority_score,
                    urgency_score  = sig.urgency_score,
                    status         = sig.status,
                    top_volunteers = [
                        MatchResult(
                            volunteer_id   = m["volunteer_id"],
                            volunteer_name = m["volunteer_name"],
                            total          = m["total"],
                            skill_score    = m["skill_score"],
                            distance_score = m["distance_score"],
                            language_score = m["language_score"],
                            trust_score    = m["trust_score"],
                        )
                        for m in top_vols
                    ],
                )
            )

        return DashboardResponse(
            total_open_signals  = total_open,
            total_volunteers    = total_volunteers,
            total_reports_today = total_reports_today,
            top_signals         = dashboard_signals,
        )

    except Exception as e:
        logger.error(f"SQL failed in get_dashboard: {e}")
        await db_manager.handle_sql_failure()
        return await _get_dashboard_firebase()
