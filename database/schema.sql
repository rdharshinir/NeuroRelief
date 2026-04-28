-- NeuroRelief Database Schema
-- PostgreSQL (PostGIS optional - remove ST_ functions if not enabled)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────
-- 1. REPORTS: raw community submissions
-- ─────────────────────────────────────────────
CREATE TABLE reports (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_lat  FLOAT NOT NULL,
    location_lon  FLOAT NOT NULL,
    issue_type    VARCHAR(100) NOT NULL,       -- e.g. "medical", "food", "shelter"
    description   TEXT NOT NULL,
    severity      INTEGER DEFAULT 1,           -- 1-5 extracted from keywords
    timestamp     TIMESTAMPTZ DEFAULT NOW(),
    signal_id     UUID REFERENCES signals(id) ON DELETE SET NULL,  -- linked fused signal
    reporter_name VARCHAR(100),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 2. SIGNALS: fused need signals
-- ─────────────────────────────────────────────
CREATE TABLE signals (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_type       VARCHAR(100) NOT NULL,
    center_lat       FLOAT NOT NULL,
    center_lon       FLOAT NOT NULL,
    report_count     INTEGER DEFAULT 1,
    base_severity    FLOAT DEFAULT 1.0,
    urgency_score    FLOAT DEFAULT 0.0,        -- base_severity * log(1 + report_count)
    priority_score   FLOAT DEFAULT 0.0,        -- urgency_score + time_decay_factor
    status           VARCHAR(50) DEFAULT 'open',  -- open | assigned | resolved
    first_seen       TIMESTAMPTZ DEFAULT NOW(),
    last_updated     TIMESTAMPTZ DEFAULT NOW(),
    assigned_volunteer_id UUID REFERENCES volunteers(id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- 3. VOLUNTEERS: registered helpers
-- ─────────────────────────────────────────────
CREATE TABLE volunteers (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         VARCHAR(150) NOT NULL,
    email        VARCHAR(200) UNIQUE,
    skills       TEXT[] NOT NULL DEFAULT '{}',     -- ["medical","driving","first_aid"]
    languages    TEXT[] NOT NULL DEFAULT '{}',     -- ["english","hindi","tamil"]
    location_lat FLOAT NOT NULL,
    location_lon FLOAT NOT NULL,
    trust_score  FLOAT DEFAULT 0.5,               -- 0.0 - 1.0
    is_available BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 4. ASSIGNMENTS: volunteer ↔ signal matches
-- ─────────────────────────────────────────────
CREATE TABLE assignments (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id      UUID REFERENCES signals(id) ON DELETE CASCADE,
    volunteer_id   UUID REFERENCES volunteers(id) ON DELETE CASCADE,
    match_score    FLOAT DEFAULT 0.0,             -- computed 4-axis score
    skill_score    FLOAT DEFAULT 0.0,
    distance_score FLOAT DEFAULT 0.0,
    language_score FLOAT DEFAULT 0.0,
    trust_score    FLOAT DEFAULT 0.0,
    status         VARCHAR(50) DEFAULT 'suggested', -- suggested | accepted | completed
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- INDEXES for performance
-- ─────────────────────────────────────────────
CREATE INDEX idx_reports_issue_type   ON reports(issue_type);
CREATE INDEX idx_reports_timestamp    ON reports(timestamp);
CREATE INDEX idx_signals_status       ON signals(status);
CREATE INDEX idx_signals_priority     ON signals(priority_score DESC);
CREATE INDEX idx_volunteers_available ON volunteers(is_available);
