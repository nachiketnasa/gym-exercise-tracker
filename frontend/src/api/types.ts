// Request and response types for the backend API.
//
// These follow the contracts documented in `_docs/plan.md`, the root README's
// "Exercise API" section, and backend issues #6–#15. Endpoints whose backend is
// not built yet are marked `provisional` — adjust once the backend lands.

// --- Exercises -------------------------------------------------------------

export type ExerciseCategory = 'strength' | 'cardio'

export interface Exercise {
  id: number
  name: string
  category: ExerciseCategory
  is_preset: boolean
  created_at: string
  updated_at: string
}

export interface CreateExerciseInput {
  name: string
  category: ExerciseCategory
}

// --- Workout sessions -----------------------------------------------------

/** provisional: the exact allowed values are set by the backend. */
export type WeightUnit = 'kg' | 'lb'

/** Metrics that can be recorded on a single session entry. */
export interface EntryMetrics {
  sets?: number
  reps?: number
  weight?: number
  weight_unit?: WeightUnit
  duration_seconds?: number
  distance_meters?: number
  pace_seconds_per_km?: number
}

export interface CreateSessionEntryInput extends EntryMetrics {
  exercise_id: number
}

/** PATCH body for an entry — every field optional. provisional. */
export type UpdateSessionEntryInput = Partial<CreateSessionEntryInput>

export interface CreateSessionInput {
  /** ISO date (YYYY-MM-DD); defaults to today server-side when omitted. */
  date?: string
  notes?: string
  entries?: CreateSessionEntryInput[]
}

export interface SessionEntry extends EntryMetrics {
  id: number
  exercise_id: number
  position: number
}

export interface Session {
  id: number
  date: string
  notes: string | null
  entries: SessionEntry[]
}

/** Row shape for the paginated history list. provisional: `primary_lifts`. */
export interface SessionSummary {
  id: number
  date: string
  exercise_count: number
  primary_lifts: string[]
}

export interface Paginated<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export interface SessionHistoryQuery {
  page?: number
  page_size?: number
  /** ISO date (YYYY-MM-DD). */
  start_date?: string
  /** ISO date (YYYY-MM-DD). */
  end_date?: string
  [key: string]: string | number | undefined
}

// --- Personal records ---------------------------------------------------

/** provisional: keyed by (exercise, metric); `value` is null until first set. */
export interface PersonalRecord {
  metric: string
  value: number | null
  achieved_on: string | null
  session_id: number | null
  entry_id: number | null
}

// --- Goals ------------------------------------------------------------------

/** provisional shape — confirm fields once the goals backend (#12) lands. */
export interface Goal {
  id: number
  exercise_id: number
  metric: string
  target_value: number
  unit: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface CreateGoalInput {
  metric: string
  target_value: number
  unit?: string
  description?: string
}

export type UpdateGoalInput = Partial<CreateGoalInput>

// --- Progress -------------------------------------------------------------

export interface ProgressQuery {
  metric: string
  /** ISO date (YYYY-MM-DD). */
  start_date?: string
  /** ISO date (YYYY-MM-DD). */
  end_date?: string
  [key: string]: string | undefined
}

export interface ProgressPoint {
  date: string
  value: number
}

// --- Errors ---------------------------------------------------------------

/**
 * Backend error envelope. #15 introduces `{ error: { ... } }`; until it lands
 * FastAPI's default `{ detail: ... }` may still appear, so tolerate both.
 */
export interface ApiErrorBody {
  error?: { message?: string; code?: string; [k: string]: unknown }
  detail?: unknown
  [k: string]: unknown
}
