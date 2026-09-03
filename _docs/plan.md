# Gym Exercise Tracker — Project Scope

## Overview
A responsive web app (mobile-friendly) for tracking gym workouts, starting as a
solo tool with detailed tracking, designed to scale later into a
multi-user, Strava-like experience.

## Usage Model
- **Platform:** Web app, responsive/mobile-friendly (not a native mobile app)
- **Users:** Just me for now; architecture should allow scaling to multiple
  users who can see each other's progress in the future
- **Logging style:** Both live-session logging (as workout happens) and
  after-the-fact summary entry

## Exercise Categories (v1)
- **Strength:** sets, reps, weight (+ unit)
- **Cardio:** duration, distance, speed/pace

*Deferred for later:* flexibility/mobility tracking

## Exercise Selection
- Preset library of common exercises (e.g. bench press, squat, running)
- Plus ability to add fully custom exercises

## Detailed Tracking Features (v1)
- Workout logging
- Progress charts/trends over time, per exercise
- Personal records (PRs) — auto-calculated best values per exercise, per metric
- Goals — target values per exercise (e.g. "bench 200lb x5", "5k under 25min")

*Deferred for later:* workout plans/templates to follow

## Data Model
- **Exercise:** name + category (strength/cardio) + relevant fields for that category
- **Workout session:** date + list of exercise entries
- **Goal:** target value(s) per exercise
- **PR:** auto-calculated, per exercise, per metric

## Core Screens
1. **Log Workout** — live or after-the-fact; pick exercise, enter sets/metrics
2. **History** — list of past sessions
3. **Exercise Detail** — progress chart + PR + goal for that exercise
4. **Goals** — set/edit targets

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React
- **Database:** PostgreSQL

## Build Approach
- Full client/server web app from the start (FastAPI API + React SPA + PostgreSQL)
- Single-user for v1, but data model and auth boundary designed so multi-user
  scoping can be added later without a rewrite

## Deliberately Deferred (Roadmap)
- Multi-user accounts
- Social/following feed (Strava-style)
- Flexibility/mobility tracking
- Workout plans/templates

## Resolved Decisions
- **PRs and goals track multiple metrics per exercise** (resolved 2026-09-03).
  PR and goal records are keyed by (exercise, metric), so bench press can hold a
  best weight, best reps, and best estimated 1RM at the same time, and a single
  exercise can have more than one active goal. Progress series (#13) selects one
  metric at a time.
