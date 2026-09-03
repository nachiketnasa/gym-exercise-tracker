// Typed client for the Gym Exercise Tracker backend.
//
// Wraps the native `fetch` — no HTTP library. One function per documented
// endpoint; all types live in `./types`.

import type {
  ApiErrorBody,
  CreateExerciseInput,
  CreateGoalInput,
  CreateSessionEntryInput,
  CreateSessionInput,
  Exercise,
  Goal,
  Paginated,
  PersonalRecord,
  ProgressPoint,
  ProgressQuery,
  Session,
  SessionEntry,
  SessionHistoryQuery,
  SessionSummary,
  UpdateGoalInput,
  UpdateSessionEntryInput,
} from './types'

/** Base URL for the backend. Override with `VITE_API_BASE_URL`. */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Distinguishes a transport failure from a completed HTTP error response. */
export type ApiErrorKind = 'network' | 'http'

/** The single error type every client function rejects with. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind
  /** HTTP status — only set when `kind === 'http'`. */
  readonly status?: number
  /** Parsed response body — only set when `kind === 'http'`. */
  readonly body?: ApiErrorBody

  constructor(
    kind: ApiErrorKind,
    message: string,
    opts: { status?: number; body?: ApiErrorBody; cause?: unknown } = {},
  ) {
    super(message, { cause: opts.cause })
    this.name = 'ApiError'
    this.kind = kind
    this.status = opts.status
    this.body = opts.body
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError
}

type QueryValue = string | number | boolean | undefined | null

/** Serialize a params object into a `?a=1&b=2` string (empty when no params). */
export function toQueryString(params: Record<string, QueryValue> = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value))
  }
  const serialized = search.toString()
  return serialized ? `?${serialized}` : ''
}

function messageFromBody(body: ApiErrorBody | undefined, status: number): string {
  const fromEnvelope = body?.error?.message
  if (typeof fromEnvelope === 'string') return fromEnvelope
  if (typeof body?.detail === 'string') return body.detail
  return `Request failed with status ${status}`
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, QueryValue>
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}${toQueryString(options.query)}`
  const init: RequestInit = { method: options.method ?? 'GET' }

  if (options.body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(options.body)
  }

  let response: Response
  try {
    response = await fetch(url, init)
  } catch (cause) {
    throw new ApiError('network', 'Network request failed', { cause })
  }

  // Read as text first so an empty body (204, or any no-content response)
  // never triggers a JSON parse error.
  const raw = await response.text()
  let parsed: unknown
  if (raw.length > 0) {
    try {
      parsed = JSON.parse(raw)
    } catch {
      parsed = undefined
    }
  }

  if (!response.ok) {
    const body = (parsed ?? undefined) as ApiErrorBody | undefined
    throw new ApiError('http', messageFromBody(body, response.status), {
      status: response.status,
      body,
    })
  }

  return parsed as T
}

// --- Exercises -------------------------------------------------------------

export function listExercises(): Promise<Exercise[]> {
  return request<Exercise[]>('/exercises')
}

export function getExercise(id: number): Promise<Exercise> {
  return request<Exercise>(`/exercises/${id}`)
}

export function createExercise(input: CreateExerciseInput): Promise<Exercise> {
  return request<Exercise>('/exercises', { method: 'POST', body: input })
}

// --- Workout sessions -----------------------------------------------------

export function createSession(input: CreateSessionInput): Promise<Session> {
  return request<Session>('/sessions', { method: 'POST', body: input })
}

export function getSession(id: number): Promise<Session> {
  return request<Session>(`/sessions/${id}`)
}

export function listSessions(
  query: SessionHistoryQuery = {},
): Promise<Paginated<SessionSummary>> {
  return request<Paginated<SessionSummary>>('/sessions', { query })
}

export function addSessionEntry(
  sessionId: number,
  input: CreateSessionEntryInput,
): Promise<SessionEntry> {
  return request<SessionEntry>(`/sessions/${sessionId}/entries`, {
    method: 'POST',
    body: input,
  })
}

export function updateSessionEntry(
  sessionId: number,
  entryId: number,
  input: UpdateSessionEntryInput,
): Promise<SessionEntry> {
  return request<SessionEntry>(`/sessions/${sessionId}/entries/${entryId}`, {
    method: 'PATCH',
    body: input,
  })
}

export function removeSessionEntry(
  sessionId: number,
  entryId: number,
): Promise<void> {
  return request<void>(`/sessions/${sessionId}/entries/${entryId}`, {
    method: 'DELETE',
  })
}

// --- History -------------------------------------------------------------

/** Alias for `listSessions` — the History screen's paginated session list. */
export const listSessionHistory = listSessions

// --- Personal records ---------------------------------------------------

export function getExercisePersonalRecords(
  exerciseId: number,
): Promise<PersonalRecord[]> {
  return request<PersonalRecord[]>(`/exercises/${exerciseId}/prs`)
}

// --- Goals ------------------------------------------------------------------

export function listGoals(exerciseId: number): Promise<Goal[]> {
  return request<Goal[]>(`/exercises/${exerciseId}/goals`)
}

export function createGoal(
  exerciseId: number,
  input: CreateGoalInput,
): Promise<Goal> {
  return request<Goal>(`/exercises/${exerciseId}/goals`, {
    method: 'POST',
    body: input,
  })
}

export function getGoal(goalId: number): Promise<Goal> {
  return request<Goal>(`/goals/${goalId}`)
}

export function updateGoal(
  goalId: number,
  input: UpdateGoalInput,
): Promise<Goal> {
  return request<Goal>(`/goals/${goalId}`, { method: 'PATCH', body: input })
}

export function deleteGoal(goalId: number): Promise<void> {
  return request<void>(`/goals/${goalId}`, { method: 'DELETE' })
}

// --- Progress -------------------------------------------------------------

export function getExerciseProgress(
  exerciseId: number,
  query: ProgressQuery,
): Promise<ProgressPoint[]> {
  return request<ProgressPoint[]>(`/exercises/${exerciseId}/progress`, { query })
}

export type * from './types'
