-- Spectra Phase 1 Database Schema
-- Run these statements in the Supabase SQL editor (Dashboard → SQL Editor)
-- auth.users is managed by Supabase Auth — no need to create it.

-- ─────────────────────────────────────────────────────────────────────────────
-- Spots
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS spots (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT NOT NULL,
    latitude             DOUBLE PRECISION NOT NULL,
    longitude            DOUBLE PRECISION NOT NULL,
    region               TEXT NOT NULL,
    nearest_buoy_id      TEXT,   -- CDIP station id  e.g. "100"
    nearest_wind_station TEXT,   -- NOAA NDBC id     e.g. "46221"
    nearest_tide_station TEXT,   -- NOAA CO-OPS id   e.g. "9410230"
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Spots are public read (no login needed to browse)
ALTER TABLE spots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Spots are publicly readable"
    ON spots FOR SELECT
    USING (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sessions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    spot_id         UUID NOT NULL REFERENCES spots(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    rating          REAL NOT NULL CHECK (rating >= 1 AND rating <= 5),
    notes           TEXT,

    -- Auto-captured conditions at session start_time
    wave_height     REAL,    -- meters (from CDIP)
    wave_period     REAL,    -- seconds
    wave_direction  REAL,    -- degrees true
    wind_speed      REAL,    -- mph (from NOAA NDBC)
    wind_direction  REAL,    -- degrees true
    tide_height     REAL,    -- feet MLLW (from NOAA CO-OPS)
    tide_phase      TEXT,    -- "rising" | "falling" | "high" | "low"
    water_temp      REAL,    -- Celsius (from CDIP)

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Row-level security: users see and manage only their own sessions
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sessions"
    ON sessions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
    ON sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
    ON sessions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
    ON sessions FOR DELETE
    USING (auth.uid() = user_id);

-- Useful indexes
CREATE INDEX IF NOT EXISTS sessions_user_id_start_time_idx
    ON sessions (user_id, start_time DESC);
