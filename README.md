# Spectra

Personal surf session tracker with **personalized** predictions.

Most surf apps tell you the forecast. Spectra learns which conditions *you* actually rate highly, then tells you when *you* will have a good session. One surfer’s 5-star day at Blacks is another’s 2-star. Generic swell charts cannot capture that.

Think Strava for surfing — log in under 30 seconds, never type in wave height, and over time get morning alerts that match your taste, not a regional average.

## The idea

A session is only useful as training data if the conditions at that exact time are attached to it. Spectra does that automatically:

1. You surf.
2. Afterward you log **spot, time window, rating (1–5), optional notes**. Target: under 30 seconds.
3. The backend looks up that spot’s buoys and stations and stores wave, wind, tide, and water temp at session start.
4. After roughly 10–15 sessions, a per-user model can start predicting your rating for upcoming conditions.

The product is the loop, not the forecast. Predictions without logged sessions are just another surf report.

## Design principles

- **Frictionless logging.** If it takes more than 30 seconds, people will not do it. Rating + spot + time is the whole form.
- **Auto-everything.** Never ask the user for wave height, period, wind, or tide. Fetch it.
- **Personalized, not generic.** A prediction is “you will like this,” not “it’s 4 ft @ 12 s.”
- **Privacy by default.** Social is opt-in and later. Phase 1 is a private journal.
- **Mobile-first.** Almost all use is iOS. The API exists to serve the phone.

## Core objects

| Object | What it is |
|---|---|
| **User** | Supabase Auth account. Owns sessions. |
| **Spot** | Named break with lat/lon and nearest CDIP buoy, NOAA wind station, NOAA tide station. Phase 1: 20 hardcoded SoCal spots. |
| **Session** | One surf: user, spot, start/end, rating 1–5, notes, plus auto-captured conditions. |
| **Conditions** | Wave height / period / direction, wind speed / direction, tide height / phase, water temp. |

Conditions are a snapshot at `start_time`, not a live forecast. That snapshot is what the model will train on.

## Product loop (target)

```
surf → log (≤30s) → conditions attached → history + stats
                                          ↓
                         10–15 sessions → personalized “go / no-go”
                                          ↓
                         morning push: spots that look good for you
```

Phase 1 only implements the first line. Predictions start in Phase 2 (rules) and Phase 3 (ML).

## What Phase 1 is (MVP)

A private log that is worth opening after a session:

- Sign up / log in
- Pick a SoCal spot
- Log a session; conditions fill in on their own
- See history and basic stats (count, average rating, streaks)

No map, no forecast, no social, no ML. Those wait until logging actually works on a phone.

## Roadmap

| Phase | What ships |
|---|---|
| **1 — MVP (now)** | Auth, session log + auto conditions, history, basic stats, 20 SoCal spots |
| **2** | Rule-based “go / no-go” from stored conditions, 50+ spots, map |
| **3** | Per-user RandomForest, confidence, push notifications |
| **4** | Analytics, spot discovery, gear suggestions |
| **5** | Travel planning, private crew sharing, optional social feed |

## How conditions are captured

On `POST /sessions` the API reads the spot’s station IDs and queries public sources. Missing sources leave fields empty rather than failing the log.

| Field | Source |
|---|---|
| Wave height, period, direction, water temp | CDIP buoy (SoCal). NOAA NDBC fallback when CDIP has no data (CDIP realtime is ~45 days). |
| Wind speed, direction | NOAA NDBC station |
| Tide height, phase (rising / falling / high / low) | NOAA CO-OPS |

All of these are free public APIs. No paid forecast provider in Phase 1.

## Architecture

```
iOS (SwiftUI)  →  FastAPI  →  Supabase (Postgres + Auth)
                      ↓
              CDIP / NOAA NDBC / NOAA CO-OPS
```

- **iOS** — native app. Offline-capable and push notifications are planned; not built yet.
- **Backend** — Python FastAPI. Auth and CRUD today; later background jobs and per-user models.
- **Database** — Postgres on Supabase. `spots` are public-read; `sessions` are per-user via RLS. The API uses the service role key for DB writes after FastAPI has checked the JWT.
- **ML (Phase 3)** — RandomForest regression trained per user, retrained after each session. Input: conditions (+ spot). Output: predicted rating.

```
spectra/
  spectra-backend/    FastAPI, condition services, schema, spot seed
  Spectra/            SwiftUI source layout (no Xcode project yet)
```

## Monetization (later)

Freemium:

- **Free** — logging, 30-day history
- **Premium ($5–10/mo)** — ML predictions, unlimited history, analytics, travel planning, push

Do not build billing until the loop is real.

## Current status

Last real product work was February 2026. Phase 1 **backend** is largely implemented; Phase 1 **iOS** is still a skeleton.

**Done**

- Tide, wind, CDIP, and NOAA buoy services, with integration tests
- Session / spot / conditions models
- Schema + 20-spot seed
- Auth, sessions CRUD with auto-condition capture, spots list, stats
- Service-role DB client (anon key cannot insert sessions under RLS)

**Not done**

- iOS: placeholder views, empty `APIService`, no Xcode project
- Live Supabase project wiring (`.env`, run `schema.sql`, seed spots)
- Anything in Phase 2+

## Running the backend

See [`spectra-backend/README.md`](spectra-backend/README.md) for env vars, schema, seed, and the smoke test.

```bash
cd spectra-backend
poetry install
poetry run uvicorn main:app --reload --port 8000
# GET /health → {"status":"ok"}
```

## What’s next

1. Point `.env` at a Supabase project, run `schema.sql`, seed spots, `poetry run python run_smoke.py`
2. Build the iOS app around the existing API (auth, log session, history, stats)
3. Only then Phase 2: rule-based predictions and a map
