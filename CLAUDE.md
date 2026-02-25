# Spectra - Project Context

## What It Is
Personal surf session tracker with ML-based personalized predictions. "Strava for Surfing" — learns YOUR preferences to predict when YOU will have good sessions. Core differentiator: personalized predictions, not generic forecasts. One surfer's 5-star session differs from another's.

## Tech Stack
- **Frontend**: SwiftUI iOS app (native, offline-capable, push notifications)
- **Backend**: Python FastAPI (RESTful, background jobs, per-user ML models)
- **Database**: PostgreSQL + TimescaleDB (Supabase Auth, time-series conditions)
- **ML**: RandomForest regression — trains per-user model, retrains after each session
- **Data Sources**: NOAA NDBC buoys, CDIP buoys, NOAA CO-OPS (tides), NOAA weather stations — all free/public

## Phase Roadmap
- **Phase 1 (MVP)** — User auth, session logging + auto-condition capture, session history, basic stats, 20 hardcoded SoCal spots
- **Phase 2** — Rule-based predictions, 50+ spots, map view
- **Phase 3** — ML predictions (RandomForest), confidence scores, push notifications
- **Phase 4** — Advanced analytics, spot discovery, gear recommendations
- **Phase 5** — Travel planning, private crew sharing, optional social feed

## Core User Loop
1. Surf a session
2. Log it post-surf in <30 seconds (spot, time, rating 1–5, optional notes)
3. Backend auto-fetches exact conditions (wave, wind, tide, water temp) from buoy/NOAA data
4. After 10–15 sessions, ML model starts generating personalized predictions and morning alerts

## Design Principles
- Frictionless logging: <30 seconds
- Auto-everything: never ask users to input wave height manually
- Privacy by default: social features opt-in
- Mobile-first: 95% iOS usage

## Current State (Phase 1 in progress)
- ✅ All condition data services (tide, wind, CDIP buoy, NOAA buoy) — fully implemented + tested
- ✅ Pydantic models (Session, Spot, Conditions)
- ✅ Supabase client setup
- ❌ API routes — all stubs returning `{"message": "Not implemented"}`
- ❌ iOS frontend — skeleton views, empty APIService, no wired network calls

## Dev Server
- `spectra-backend`: `bash -c "cd spectra-backend && poetry run uvicorn main:app --reload --port 8000"`
- Health check: `GET /health`

## Monetization (Future)
Freemium: free tier (basic logging, 30-day history) + Premium $5–10/mo (ML predictions, unlimited history, analytics, travel planning, push notifications).
