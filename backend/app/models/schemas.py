"""
Pydantic schemas – request bodies & response models
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


# ─────────────────────────────────────────────
# REPORT schemas
# ─────────────────────────────────────────────

class ReportCreate(BaseModel):
    location_lat:  float  = Field(..., ge=-90,  le=90,  example=13.0827)
    location_lon:  float  = Field(..., ge=-180, le=180, example=80.2707)
    issue_type:    str    = Field(..., example="medical")
    description:   str    = Field(..., min_length=5, example="Urgent medical help needed")
    reporter_name: Optional[str] = Field(None, example="Ravi Kumar")
    timestamp:     Optional[datetime] = None  # defaults to now if omitted

class ReportOut(BaseModel):
    id:            UUID
    location_lat:  float
    location_lon:  float
    issue_type:    str
    description:   str
    severity:      int
    timestamp:     datetime
    signal_id:     Optional[UUID]
    reporter_name: Optional[str]
    created_at:    datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# SIGNAL schemas
# ─────────────────────────────────────────────

class SignalOut(BaseModel):
    id:               UUID
    issue_type:       str
    center_lat:       float
    center_lon:       float
    report_count:     int
    base_severity:    float
    urgency_score:    float
    priority_score:   float
    status:           str
    first_seen:       datetime
    last_updated:     datetime
    assigned_volunteer_id: Optional[UUID]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# VOLUNTEER schemas
# ─────────────────────────────────────────────

class VolunteerCreate(BaseModel):
    name:         str   = Field(..., example="Priya Sharma")
    email:        Optional[str] = Field(None, example="priya@example.com")
    skills:       list[str] = Field(default=[], example=["medical", "first_aid"])
    languages:    list[str] = Field(default=[], example=["english", "tamil"])
    location_lat: float = Field(..., ge=-90,  le=90)
    location_lon: float = Field(..., ge=-180, le=180)
    trust_score:  float = Field(default=0.5, ge=0.0, le=1.0)
    is_available: bool  = True

class VolunteerOut(BaseModel):
    id:           UUID
    name:         str
    email:        Optional[str]
    skills:       list[str]
    languages:    list[str]
    location_lat: float
    location_lon: float
    trust_score:  float
    is_available: bool
    created_at:   datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# ASSIGNMENT / MATCH schemas
# ─────────────────────────────────────────────

class MatchResult(BaseModel):
    volunteer_id:   UUID
    volunteer_name: str
    total:          float
    skill_score:    float
    distance_score: float
    language_score: float
    trust_score:    float

class AssignmentOut(BaseModel):
    id:             UUID
    signal_id:      UUID
    volunteer_id:   UUID
    match_score:    float
    skill_score:    float
    distance_score: float
    language_score: float
    trust_score:    float
    status:         str
    created_at:     datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# DASHBOARD summary schema
# ─────────────────────────────────────────────

class DashboardSignal(BaseModel):
    id:             UUID
    issue_type:     str
    center_lat:     float
    center_lon:     float
    report_count:   int
    priority_score: float
    urgency_score:  float
    status:         str
    top_volunteers: list[MatchResult] = []

class DashboardResponse(BaseModel):
    total_open_signals:   int
    total_volunteers:     int
    total_reports_today:  int
    top_signals:          list[DashboardSignal]
