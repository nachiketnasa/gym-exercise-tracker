import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSession, isApiError, listExercises, listSessions } from '../api/client'
import type {
  Exercise,
  ExerciseCategory,
  Session,
  SessionEntry,
  SessionSummary,
} from '../api/types'
import './History.css'

const PAGE_SIZE = 20

function errorMessage(err: unknown): string {
  if (isApiError(err)) return err.message
  return err instanceof Error ? err.message : 'Something went wrong'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function History() {
  const [rows, setRows] = useState<SessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [nextPage, setNextPage] = useState(1)

  const [firstStatus, setFirstStatus] = useState<'loading' | 'error' | 'ready'>(
    'loading',
  )
  const [firstNonce, setFirstNonce] = useState(0)
  const [pageLoading, setPageLoading] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)

  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => {
    let active = true
    listSessions({ page: 1, page_size: PAGE_SIZE })
      .then((res) => {
        if (!active) return
        setRows(res.items)
        setTotal(res.total)
        setNextPage(2)
        setFirstStatus('ready')
      })
      .catch(() => {
        if (active) setFirstStatus('error')
      })
    return () => {
      active = false
    }
  }, [firstNonce])

  function loadMore() {
    setPageLoading(true)
    setPageError(null)
    listSessions({ page: nextPage, page_size: PAGE_SIZE })
      .then((res) => {
        setRows((prev) => {
          const seen = new Set(prev.map((r) => r.id))
          return [...prev, ...res.items.filter((r) => !seen.has(r.id))]
        })
        setTotal(res.total)
        setNextPage((p) => p + 1)
      })
      .catch((err) => setPageError(errorMessage(err)))
      .finally(() => setPageLoading(false))
  }

  if (selected !== null) {
    return (
      <SessionDetail
        sessionId={selected}
        onBack={() => setSelected(null)}
      />
    )
  }

  if (firstStatus === 'loading') {
    return (
      <section>
        <h1>History</h1>
        <p role="status">Loading history…</p>
      </section>
    )
  }

  if (firstStatus === 'error') {
    return (
      <section>
        <h1>History</h1>
        <div role="alert">
          <p>Could not load your history.</p>
          <button
            type="button"
            onClick={() => {
              setFirstStatus('loading')
              setFirstNonce((n) => n + 1)
            }}
          >
            Retry
          </button>
        </div>
      </section>
    )
  }

  if (rows.length === 0) {
    return (
      <section>
        <h1>History</h1>
        <p>No workout history yet.</p>
        <Link to="/">Log your first workout</Link>
      </section>
    )
  }

  const hasMore = rows.length < total

  return (
    <section className="history">
      <h1>History</h1>
      <ul className="session-list" aria-label="Workout sessions">
        {rows.map((row) => (
          <li key={row.id}>
            <button type="button" onClick={() => setSelected(row.id)}>
              <span className="session-date">{formatDate(row.date)}</span>
              <span className="session-summary">
                {row.exercise_count}{' '}
                {row.exercise_count === 1 ? 'exercise' : 'exercises'}
                {row.primary_lifts.length > 0 &&
                  ` — ${row.primary_lifts.join(', ')}`}
              </span>
            </button>
          </li>
        ))}
      </ul>

      {pageError && (
        <div role="alert">
          <p>Could not load more sessions: {pageError}</p>
          <button type="button" onClick={loadMore}>
            Retry
          </button>
        </div>
      )}

      {hasMore && !pageError && (
        <button type="button" onClick={loadMore} disabled={pageLoading}>
          {pageLoading ? 'Loading…' : 'Load more'}
        </button>
      )}
      {!hasMore && <p className="end-note">End of history.</p>}
    </section>
  )
}

interface SessionDetailProps {
  sessionId: number
  onBack: () => void
}

function categoryOf(
  entry: SessionEntry,
  exercise: Exercise | undefined,
): ExerciseCategory {
  if (exercise) return exercise.category
  if (
    entry.duration_seconds != null ||
    entry.distance_meters != null ||
    entry.pace_seconds_per_km != null
  ) {
    return 'cardio'
  }
  return 'strength'
}

function metricRows(
  entry: SessionEntry,
  category: ExerciseCategory,
): Array<[string, string]> {
  const dash = (v: unknown) => (v == null ? '—' : String(v))
  if (category === 'cardio') {
    return [
      ['Duration', entry.duration_seconds == null ? '—' : `${entry.duration_seconds} s`],
      ['Distance', entry.distance_meters == null ? '—' : `${entry.distance_meters} m`],
      ['Pace', entry.pace_seconds_per_km == null ? '—' : `${entry.pace_seconds_per_km} s/km`],
    ]
  }
  return [
    ['Sets', dash(entry.sets)],
    ['Reps', dash(entry.reps)],
    [
      'Weight',
      entry.weight == null
        ? '—'
        : `${entry.weight} ${entry.weight_unit ?? ''}`.trim(),
    ],
  ]
}

function SessionDetail({ sessionId, onBack }: SessionDetailProps) {
  const [session, setSession] = useState<Session | null>(null)
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([getSession(sessionId), listExercises().catch(() => [])])
      .then(([s, list]) => {
        if (!active) return
        setSession(s)
        setExercises(list)
        setStatus('ready')
      })
      .catch(() => {
        if (active) setStatus('error')
      })
    return () => {
      active = false
    }
  }, [sessionId, nonce])

  return (
    <section className="session-detail">
      <button type="button" onClick={onBack}>
        ← Back to history
      </button>
      <h1>Session detail</h1>

      {status === 'loading' && <p role="status">Loading session…</p>}

      {status === 'error' && (
        <div role="alert">
          <p>Could not load this session.</p>
          <button
            type="button"
            onClick={() => {
              setStatus('loading')
              setNonce((n) => n + 1)
            }}
          >
            Retry
          </button>
        </div>
      )}

      {status === 'ready' && session && (
        <>
          <p className="session-date">{formatDate(session.date)}</p>
          {session.notes && <p className="session-notes">{session.notes}</p>}
          {session.entries.length === 0 ? (
            <p>No exercises recorded.</p>
          ) : (
            <ol className="entry-list">
              {session.entries.map((entry) => {
                const exercise = exercises.find(
                  (e) => e.id === entry.exercise_id,
                )
                const category = categoryOf(entry, exercise)
                return (
                  <li key={entry.id}>
                    <strong>
                      {exercise ? exercise.name : `Exercise #${entry.exercise_id}`}
                    </strong>
                    <dl>
                      {metricRows(entry, category).map(([label, value]) => (
                        <div key={label}>
                          <dt>{label}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  </li>
                )
              })}
            </ol>
          )}
        </>
      )}
    </section>
  )
}
