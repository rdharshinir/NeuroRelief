"""
NeuroRelief – Signal Fusion & Priority Engine
Core algorithms: severity extraction (Gemma 4 AI + keyword fallback),
signal fusion, priority scoring, geo-affinity matching
"""
import math
import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("neurorelief.algorithms")

# ─────────────────────────────────────────────────────────────────────────────
# 1. SEVERITY EXTRACTION (Gemma 4 AI-powered + keyword fallback)
# ─────────────────────────────────────────────────────────────────────────────

# Keyword → severity level mapping (1-5 scale) — used as fallback
SEVERITY_KEYWORDS: dict[str, int] = {
    # Critical (5)
    "critical": 5, "life-threatening": 5, "emergency": 5, "dying": 5, "death": 5,
    # Urgent (4)
    "urgent": 4, "severe": 4, "serious": 4, "immediate": 4, "dire": 4,
    # High (3)
    "high": 3, "bad": 3, "important": 3, "significant": 3, "needed": 3,
    # Medium (2)
    "moderate": 2, "medium": 2, "concerning": 2, "some": 2,
    # Low (1)
    "minor": 1, "low": 1, "small": 1, "slight": 1,
}

# ── Gemma 4 AI Client (lazy init) ────────────────────────────────────────────
_genai_client = None
_gemma4_available = False


def _init_gemma4():
    """Lazy-initialise the Gemma 4 client via Google GenAI SDK."""
    global _genai_client, _gemma4_available
    if _genai_client is not None:
        return _gemma4_available

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("GEMINI_API_KEY not set – using keyword-based severity extraction")
        _gemma4_available = False
        return False

    try:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
        _gemma4_available = True
        logger.info("Gemma 4 AI model initialised for severity extraction")
        return True
    except Exception as e:
        logger.warning(f"Failed to initialise Gemma 4: {e}. Falling back to keywords.")
        _gemma4_available = False
        return False


def _extract_severity_gemma4(description: str, issue_type: str) -> Optional[int]:
    """
    Use Gemma 4 AI to analyse report description and extract severity (1-5).
    Returns None if AI is unavailable or fails.
    """
    if not _init_gemma4() or _genai_client is None:
        return None

    try:
        prompt = (
            "You are a disaster relief severity classifier. "
            "Analyse the following community report and return ONLY a single integer "
            "from 1 to 5 representing the severity level:\n"
            "  1 = Minor (low urgency, no immediate danger)\n"
            "  2 = Moderate (some concern, can wait hours)\n"
            "  3 = High (significant need, respond within hours)\n"
            "  4 = Urgent (severe situation, respond within 1 hour)\n"
            "  5 = Critical (life-threatening, immediate response needed)\n\n"
            f"Issue Type: {issue_type}\n"
            f"Report: {description}\n\n"
            "Respond with ONLY the number (1-5), nothing else."
        )

        response = _genai_client.models.generate_content(
            model="gemma-4-31b-it",
            contents=prompt,
            config={
                "system_instruction": (
                    "You are an expert disaster relief triage system. "
                    "You must respond with exactly one digit (1-5) and nothing else."
                ),
            },
        )

        result = response.text.strip()
        # Parse the single digit response
        severity = int(result[0]) if result and result[0].isdigit() else None
        if severity and 1 <= severity <= 5:
            logger.debug(f"Gemma 4 severity={severity} for: {description[:50]}...")
            return severity
        logger.warning(f"Gemma 4 returned unexpected value: {result}")
        return None
    except Exception as e:
        logger.warning(f"Gemma 4 severity extraction failed: {e}")
        return None


def _extract_severity_keywords(description: str, issue_type: str) -> int:
    """Keyword-based severity extraction (fallback). Returns 1-5."""
    text = (description + " " + issue_type).lower()
    max_severity = 2  # default moderate
    for keyword, level in SEVERITY_KEYWORDS.items():
        if keyword in text:
            max_severity = max(max_severity, level)
    return max_severity


def extract_severity(description: str, issue_type: str = "") -> int:
    """
    Extract severity score (1-5) from report description.
    Strategy:
      1. Try Gemma 4 AI analysis (if GEMINI_API_KEY is configured)
      2. Fallback to keyword-based extraction
    """
    # Try AI first
    ai_severity = _extract_severity_gemma4(description, issue_type)
    if ai_severity is not None:
        return ai_severity

    # Fallback to keywords
    return _extract_severity_keywords(description, issue_type)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GEO DISTANCE (Haversine formula)
# ─────────────────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance in km between two lat/lon points.
    Uses the Haversine formula.
    """
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ─────────────────────────────────────────────────────────────────────────────
# 3. SIGNAL FUSION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compute_urgency_score(base_severity: float, report_count: int) -> float:
    """
    Corroboration-weighted urgency:
        urgency_score = base_severity * log(1 + report_count)

    Logic: More corroborating reports increase confidence, boosted logarithmically
    to prevent a single flood of low-quality reports from dominating.
    """
    return round(base_severity * math.log(1 + report_count), 4)


def should_merge_reports(
    existing_lat: float, existing_lon: float, existing_issue: str, existing_ts: datetime,
    new_lat: float, new_lon: float, new_issue: str, new_ts: datetime,
    radius_km: float = 1.0,
    time_window_hours: float = 24.0,
) -> bool:
    """
    Determine if a new report should be merged into an existing signal.
    Merge criteria:
      - Same issue_type (case-insensitive)
      - Within radius_km (default 1 km)
      - Within time_window_hours (default 24 h)
    """
    # Ensure timezone-aware comparison
    if existing_ts.tzinfo is None:
        existing_ts = existing_ts.replace(tzinfo=timezone.utc)
    if new_ts.tzinfo is None:
        new_ts = new_ts.replace(tzinfo=timezone.utc)

    same_type = existing_issue.lower() == new_issue.lower()
    close_enough = haversine_km(existing_lat, existing_lon, new_lat, new_lon) <= radius_km
    recent_enough = abs((new_ts - existing_ts).total_seconds()) <= time_window_hours * 3600

    return same_type and close_enough and recent_enough


def compute_new_centroid(
    existing_lat: float, existing_lon: float, existing_count: int,
    new_lat: float, new_lon: float,
) -> tuple[float, float]:
    """
    Incrementally update signal centroid when a new report is merged.
    Uses weighted average to keep centroid accurate as reports accumulate.
    """
    new_count = existing_count + 1
    center_lat = (existing_lat * existing_count + new_lat) / new_count
    center_lon = (existing_lon * existing_count + new_lon) / new_count
    return round(center_lat, 6), round(center_lon, 6)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRIORITY ENGINE (time-decay scoring)
# ─────────────────────────────────────────────────────────────────────────────

def compute_time_decay(first_seen: datetime, half_life_hours: float = 12.0) -> float:
    """
    Exponential time-decay factor: older signals lose priority.
        decay = exp(-lambda * age_hours)
    where lambda = ln(2) / half_life_hours

    A signal halves in time-priority every `half_life_hours` hours.
    """
    now = datetime.now(timezone.utc)
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)

    age_hours = (now - first_seen).total_seconds() / 3600
    lam = math.log(2) / half_life_hours
    return round(math.exp(-lam * age_hours), 4)


def compute_priority_score(urgency_score: float, first_seen: datetime) -> float:
    """
    Final priority ranking score:
        priority = urgency_score + time_decay_factor

    urgency_score captures severity × corroboration;
    time_decay keeps fresh signals at top even if less corroborated.
    """
    decay = compute_time_decay(first_seen)
    return round(urgency_score + decay, 4)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GEO-AFFINITY MATCHING ENGINE (4-axis)
# ─────────────────────────────────────────────────────────────────────────────

# Axis weights (must sum to 1.0)
MATCH_WEIGHTS = {
    "skill":    0.35,
    "distance": 0.25,
    "language": 0.20,
    "trust":    0.20,
}

# Distance scoring: max useful range = 50 km (score drops to 0 beyond this)
MAX_DISTANCE_KM = 50.0


def compute_skill_score(volunteer_skills: list[str], required_skills: list[str]) -> float:
    """
    Jaccard-like overlap between volunteer skills and signal required skills.
    Returns 0.0–1.0. If no required skills, returns 0.5 (neutral).
    """
    if not required_skills:
        return 0.5
    v_set = {s.lower().strip() for s in volunteer_skills}
    r_set = {s.lower().strip() for s in required_skills}
    overlap = len(v_set & r_set)
    return round(overlap / len(r_set), 4)


def compute_distance_score(
    vol_lat: float, vol_lon: float,
    sig_lat: float, sig_lon: float,
) -> float:
    """
    Inverse-distance score normalised to MAX_DISTANCE_KM.
    Volunteers within 1 km get score ≈ 1.0; at MAX_DISTANCE_KM → 0.0.
    """
    dist = haversine_km(vol_lat, vol_lon, sig_lat, sig_lon)
    if dist >= MAX_DISTANCE_KM:
        return 0.0
    return round(1.0 - (dist / MAX_DISTANCE_KM), 4)


def compute_language_score(volunteer_langs: list[str], required_langs: list[str]) -> float:
    """
    Language match ratio. Returns 1.0 if any language matches.
    Returns 0.5 if no required languages specified.
    """
    if not required_langs:
        return 0.5
    v_set = {l.lower().strip() for l in volunteer_langs}
    r_set = {l.lower().strip() for l in required_langs}
    return 1.0 if v_set & r_set else 0.0


def compute_match_score(
    volunteer_skills: list[str],
    vol_lat: float, vol_lon: float,
    volunteer_langs: list[str],
    trust_score: float,
    required_skills: list[str],
    sig_lat: float, sig_lon: float,
    required_langs: list[str],
) -> dict:
    """
    Core 4-axis geo-affinity match score formula:

        match_score = (skill_match  * 0.35)
                    + (distance_score * 0.25)
                    + (language_match * 0.20)
                    + (trust_score   * 0.20)

    Returns a dict with all component scores + final total.
    """
    skill    = compute_skill_score(volunteer_skills, required_skills)
    distance = compute_distance_score(vol_lat, vol_lon, sig_lat, sig_lon)
    language = compute_language_score(volunteer_langs, required_langs)
    trust    = min(max(trust_score, 0.0), 1.0)  # clamp to [0,1]

    total = round(
        skill    * MATCH_WEIGHTS["skill"]    +
        distance * MATCH_WEIGHTS["distance"] +
        language * MATCH_WEIGHTS["language"] +
        trust    * MATCH_WEIGHTS["trust"],
        4
    )

    return {
        "total":         total,
        "skill_score":   skill,
        "distance_score": distance,
        "language_score": language,
        "trust_score":   trust,
    }


def rank_volunteers(
    volunteers: list[dict],
    signal: dict,
    top_n: int = 3,
) -> list[dict]:
    """
    Rank available volunteers by 4-axis match score for a given signal.
    Returns top_n volunteers with their component scores.

    volunteers: list of dicts with keys:
        id, name, skills, languages, location_lat, location_lon,
        trust_score, is_available

    signal: dict with keys:
        issue_type, center_lat, center_lon, required_skills, required_langs
    """
    results = []
    for vol in volunteers:
        if not vol.get("is_available", True):
            continue  # skip unavailable volunteers

        scores = compute_match_score(
            volunteer_skills=vol.get("skills", []),
            vol_lat=vol["location_lat"],
            vol_lon=vol["location_lon"],
            volunteer_langs=vol.get("languages", []),
            trust_score=vol.get("trust_score", 0.5),
            required_skills=signal.get("required_skills", []),
            sig_lat=signal["center_lat"],
            sig_lon=signal["center_lon"],
            required_langs=signal.get("required_langs", []),
        )

        results.append({
            "volunteer_id":    vol["id"],
            "volunteer_name":  vol.get("name", "Unknown"),
            **scores,
        })

    # Sort descending by total match score
    results.sort(key=lambda x: x["total"], reverse=True)
    return results[:top_n]
