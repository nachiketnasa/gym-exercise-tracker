import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  getExercise,
  getExercisePersonalRecords,
  getExerciseProgress,
  isApiError,
  listGoals,
} from '../api/client'
import type {
  Exercise,
  ExerciseCategory,
  Goal,
  PersonalRecord,
  ProgressPoint,
} from '../api/types'
import './ExerciseDetail.css'

const METRICS: Record<ExerciseCategory, string[]> = {
  strength: ['weight', 'reps', 'estimated_1rm'],
  cardio: ['distance', 'pace', 'duration'],
}

const METRIC_LABELS: Record<string, string> = {
  weight: 'weight',
  reps: 'reps',
  estimated_1rm: 'estimated 1RM',
  distance: 'distance',
  pace: 'pace',
  duration: 'duration',
}

function unitForMetric(metric: string): string {
  switch (metric) {
    case 'weight':
    case 'estimated_1rm':
      return 'kg'
    case 'distance':
      return 'm'
    case 'duration':
      return 's'
    case 'pace':
      return 's/km'
    default:
      return ''
  }
}

function primaryMetric(category: ExerciseCategory): string {
  return category === 'strength' ? 'weight' : 'distance'
}

export default function ExerciseDetail() {
  const { exerciseId } = useParams<{ exerciseId: string }>()
  const id = Number(exerciseId)

  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [status, setStatus] = useState<
    'loading' | 'notfound' | 'error' | 'ready'
  >('loading')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let active = true
    getExercise(id)
      .then((ex) => {
        if (!active) return
        setExercise(ex)
        setStatus('ready')
      })
      .catch((err) => {
        if (!active) return
        setStatus(isApiError(err) && err.status === 404 ? 'notfound' : 'error')
      })
    return () => {
      active = false
    }
  }, [id, nonce])

  if (status === 'loading') {
    return (
      <section>
        <h1>Exercise</h1>
        <p role="status">Loading exercise…</p>
      </section>
    )
  }

  if (status === 'notfound') {
    return (
      <section>
        <h1>Exercise not found</h1>
        <p>No exercise exists with id {exerciseId}.</p>
        <Link to="/history">Back to history</Link>
      </section>
    )
  }

  if (status === 'error' || !exercise) {
    return (
      <section>
        <h1>Exercise</h1>
        <div role="alert">
          <p>Could not load this exercise.</p>
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
      </section>
    )
  }

  return (
    <section className="exercise-detail">
      <h1>{exercise.name}</h1>
      <p className="category">Category: {exercise.category}</p>

      <ProgressSection exerciseId={id} category={exercise.category} />
      <PrSection exerciseId={id} />
      <GoalsSection exerciseId={id} />
    </section>
  )
}

function ProgressSection({
  exerciseId,
  category,
}: {
  exerciseId: number
  category: ExerciseCategory
}) {
  const [metric, setMetric] = useState(() => primaryMetric(category))
  const [points, setPoints] = useState<ProgressPoint[]>([])
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let active = true
    getExerciseProgress(exerciseId, { metric })
      .then((data) => {
        if (!active) return
        setPoints([...data].sort((a, b) => a.date.localeCompare(b.date)))
        setStatus('ready')
      })
      .catch(() => {
        if (active) setStatus('error')
      })
    return () => {
      active = false
    }
  }, [exerciseId, metric, nonce])

  const unit = unitForMetric(metric)

  return (
    <section className="panel" aria-labelledby="progress-heading">
      <h2 id="progress-heading">Progress</h2>

      <label className="field">
        <span>Metric</span>
        <select
          value={metric}
          onChange={(e) => {
            setStatus('loading')
            setMetric(e.target.value)
          }}
        >
          {METRICS[category].map((m) => (
            <option key={m} value={m}>
              {METRIC_LABELS[m]}
            </option>
          ))}
        </select>
      </label>

      <p className="caption">
        {METRIC_LABELS[metric]}
        {unit ? ` (${unit})` : ''} over time
      </p>

      {status === 'loading' && <p role="status">Loading progress…</p>}

      {status === 'error' && (
        <div role="alert">
          <p>Could not load progress.</p>
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

      {status === 'ready' && points.length === 0 && (
        <p className="empty">No data logged for this metric yet.</p>
      )}

      {status === 'ready' && points.length > 0 && (
        <div data-testid="progress-chart">
          <LineChart width={560} height={280} data={points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" name="Date" />
            <YAxis name={`${METRIC_LABELS[metric]}${unit ? ` (${unit})` : ''}`} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#3366cc" />
          </LineChart>
        </div>
      )}
    </section>
  )
}

function PrSection({ exerciseId }: { exerciseId: number }) {
  const [prs, setPrs] = useState<PersonalRecord[]>([])
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let active = true
    getExercisePersonalRecords(exerciseId)
      .then((data) => {
        if (!active) return
        setPrs(data.filter((pr) => pr.value !== null))
        setStatus('ready')
      })
      .catch(() => {
        if (active) setStatus('error')
      })
    return () => {
      active = false
    }
  }, [exerciseId, nonce])

  return (
    <section className="panel" aria-labelledby="pr-heading">
      <h2 id="pr-heading">Personal records</h2>

      {status === 'loading' && <p role="status">Loading personal records…</p>}

      {status === 'error' && (
        <div role="alert">
          <p>Could not load personal records.</p>
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

      {status === 'ready' &&
        (prs.length === 0 ? (
          <p className="empty">No personal records yet.</p>
        ) : (
          <ul>
            {prs.map((pr) => (
              <li key={pr.metric}>
                {METRIC_LABELS[pr.metric] ?? pr.metric}: {pr.value}{' '}
                {unitForMetric(pr.metric)}
                {pr.achieved_on ? ` (achieved ${pr.achieved_on})` : ''}
              </li>
            ))}
          </ul>
        ))}
    </section>
  )
}

function describeGoal(goal: Goal): string {
  const metric = METRIC_LABELS[goal.metric] ?? goal.metric
  const unit = goal.unit ? ` ${goal.unit}` : ''
  const base = `target ${metric} ${goal.target_value}${unit}`
  return goal.description ? `${base} (${goal.description})` : base
}

function GoalsSection({ exerciseId }: { exerciseId: number }) {
  const [goals, setGoals] = useState<Goal[]>([])
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let active = true
    listGoals(exerciseId)
      .then((data) => {
        if (!active) return
        setGoals(data)
        setStatus('ready')
      })
      .catch(() => {
        if (active) setStatus('error')
      })
    return () => {
      active = false
    }
  }, [exerciseId, nonce])

  return (
    <section className="panel" aria-labelledby="goals-heading">
      <h2 id="goals-heading">Goals</h2>

      {status === 'loading' && <p role="status">Loading goals…</p>}

      {status === 'error' && (
        <div role="alert">
          <p>Could not load goals.</p>
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

      {status === 'ready' && (
        <>
          {goals.length === 0 ? (
            <p className="empty">No active goals for this exercise.</p>
          ) : (
            <ul>
              {goals.map((goal) => (
                <li key={goal.id}>{describeGoal(goal)}</li>
              ))}
            </ul>
          )}
          <Link to="/goals">Add or edit goals</Link>
        </>
      )}
    </section>
  )
}
