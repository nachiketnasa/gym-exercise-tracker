import { useEffect, useState } from 'react'
import {
  createGoal,
  deleteGoal,
  isApiError,
  listExercises,
  listGoals,
  updateGoal,
} from '../api/client'
import type {
  CreateGoalInput,
  Exercise,
  ExerciseCategory,
  Goal,
} from '../api/types'
import './Goals.css'

function errorMessage(err: unknown): string {
  if (isApiError(err)) return err.message
  return err instanceof Error ? err.message : 'Something went wrong'
}

function positive(value: string): number | null {
  if (value.trim() === '') return null
  const n = Number(value)
  if (!Number.isFinite(n) || n <= 0) return null
  return n
}

const METRICS: Record<ExerciseCategory, string[]> = {
  strength: ['weight', 'reps', 'estimated_1rm'],
  cardio: ['distance', 'duration', 'pace'],
}

const METRIC_LABELS: Record<string, string> = {
  weight: 'weight',
  reps: 'reps',
  estimated_1rm: 'estimated 1RM',
  distance: 'distance',
  duration: 'duration',
  pace: 'pace',
}

function defaultUnit(metric: string): string {
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

interface GoalRow {
  goal: Goal
  exercise: Exercise
}

function describe(row: GoalRow): string {
  const { goal, exercise } = row
  const metric = METRIC_LABELS[goal.metric] ?? goal.metric
  const unit = goal.unit ? ` ${goal.unit}` : ''
  const base = `${exercise.name}: target ${metric} ${goal.target_value}${unit}`
  return goal.description ? `${base} (${goal.description})` : base
}

interface FormState {
  editingId: number | null
  exerciseId: string
  metric: string
  target: string
  unit: string
  description: string
}

const EMPTY_FORM: FormState = {
  editingId: null,
  exerciseId: '',
  metric: '',
  target: '',
  unit: '',
  description: '',
}

export default function Goals() {
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [rows, setRows] = useState<GoalRow[]>([])
  const [status, setStatus] = useState<'loading' | 'error' | 'ready'>('loading')
  const [nonce, setNonce] = useState(0)

  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [rowError, setRowError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    listExercises()
      .then((list) =>
        Promise.all(
          list.map((exercise) =>
            listGoals(exercise.id).then((goals) =>
              goals.map((goal) => ({ goal, exercise })),
            ),
          ),
        ).then((perExercise) => {
          if (!active) return
          setExercises(list)
          setRows(perExercise.flat())
          setStatus('ready')
        }),
      )
      .catch(() => {
        if (active) setStatus('error')
      })
    return () => {
      active = false
    }
  }, [nonce])

  const selectedExercise = exercises.find(
    (e) => String(e.id) === form.exerciseId,
  )
  const metricOptions = selectedExercise ? METRICS[selectedExercise.category] : []

  function updateForm(patch: Partial<FormState>) {
    setForm((prev) => ({ ...prev, ...patch }))
  }

  function startCreate() {
    setForm(EMPTY_FORM)
    setFormError(null)
    setFieldErrors({})
  }

  function startEdit(row: GoalRow) {
    setForm({
      editingId: row.goal.id,
      exerciseId: String(row.exercise.id),
      metric: row.goal.metric,
      target: String(row.goal.target_value),
      unit: row.goal.unit ?? '',
      description: row.goal.description ?? '',
    })
    setFormError(null)
    setFieldErrors({})
  }

  function validate(): { input: CreateGoalInput; exerciseId: number } | null {
    const errs: Record<string, string> = {}
    const exId = Number(form.exerciseId)
    if (!form.exerciseId || Number.isNaN(exId)) {
      errs.exercise = 'Choose an exercise'
    }
    if (!form.metric) errs.metric = 'Choose a metric'
    const target = positive(form.target)
    if (target === null) errs.target = 'Enter a positive target value'
    setFieldErrors(errs)
    if (Object.keys(errs).length > 0 || target === null) return null
    return {
      exerciseId: exId,
      input: {
        metric: form.metric,
        target_value: target,
        unit: form.unit.trim() || undefined,
        description: form.description.trim() || undefined,
      },
    }
  }

  function submit() {
    const valid = validate()
    if (!valid) return
    setSaving(true)
    setFormError(null)

    const done = (goal: Goal) => {
      const exercise = exercises.find((e) => e.id === valid.exerciseId)!
      setRows((prev) => {
        if (form.editingId === null) return [...prev, { goal, exercise }]
        return prev.map((r) => (r.goal.id === goal.id ? { goal, exercise } : r))
      })
      startCreate()
    }

    const req =
      form.editingId === null
        ? createGoal(valid.exerciseId, valid.input)
        : updateGoal(form.editingId, valid.input)

    req
      .then(done)
      .catch((err) => setFormError(errorMessage(err)))
      .finally(() => setSaving(false))
  }

  function remove(row: GoalRow) {
    if (!window.confirm(`Delete this goal for ${row.exercise.name}?`)) return
    setRowError(null)
    deleteGoal(row.goal.id)
      .then(() =>
        setRows((prev) => prev.filter((r) => r.goal.id !== row.goal.id)),
      )
      .catch((err) => setRowError(errorMessage(err)))
  }

  if (status === 'loading') {
    return (
      <section>
        <h1>Goals</h1>
        <p role="status">Loading goals…</p>
      </section>
    )
  }

  if (status === 'error') {
    return (
      <section>
        <h1>Goals</h1>
        <div role="alert">
          <p>Could not load your goals.</p>
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
    <section className="goals">
      <h1>Goals</h1>

      {rows.length === 0 ? (
        <p>No goals yet. Use the form below to create your first goal.</p>
      ) : (
        <ul className="goal-list" aria-label="Goals">
          {rows.map((row) => (
            <li key={row.goal.id}>
              <span>{describe(row)}</span>
              <button type="button" onClick={() => startEdit(row)}>
                Edit
              </button>
              <button type="button" onClick={() => remove(row)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      {rowError && (
        <p role="alert" className="error">
          Delete failed: {rowError}
        </p>
      )}

      <form
        className="goal-form"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <h2>{form.editingId === null ? 'Create a goal' : 'Edit goal'}</h2>

        <label className="field">
          <span>Exercise</span>
          <select
            value={form.exerciseId}
            onChange={(e) =>
              updateForm({ exerciseId: e.target.value, metric: '', unit: '' })
            }
          >
            <option value="">Choose…</option>
            {exercises.map((exercise) => (
              <option key={exercise.id} value={exercise.id}>
                {exercise.name} ({exercise.category})
              </option>
            ))}
          </select>
        </label>
        {fieldErrors.exercise && (
          <p role="alert" className="error">
            {fieldErrors.exercise}
          </p>
        )}

        <label className="field">
          <span>Target metric</span>
          <select
            value={form.metric}
            onChange={(e) =>
              updateForm({
                metric: e.target.value,
                unit: defaultUnit(e.target.value),
              })
            }
            disabled={!selectedExercise}
          >
            <option value="">Choose…</option>
            {metricOptions.map((metric) => (
              <option key={metric} value={metric}>
                {METRIC_LABELS[metric]}
              </option>
            ))}
          </select>
        </label>
        {fieldErrors.metric && (
          <p role="alert" className="error">
            {fieldErrors.metric}
          </p>
        )}

        <label className="field">
          <span>Target value</span>
          <input
            type="number"
            value={form.target}
            onChange={(e) => updateForm({ target: e.target.value })}
          />
        </label>
        {fieldErrors.target && (
          <p role="alert" className="error">
            {fieldErrors.target}
          </p>
        )}

        <label className="field">
          <span>Unit</span>
          <input
            value={form.unit}
            onChange={(e) => updateForm({ unit: e.target.value })}
            placeholder="e.g. kg, m, s/km"
          />
        </label>

        <label className="field">
          <span>Description (optional)</span>
          <input
            value={form.description}
            onChange={(e) => updateForm({ description: e.target.value })}
            placeholder="e.g. bench 90kg x5"
          />
        </label>

        {formError && (
          <p role="alert" className="error">
            {form.editingId === null ? 'Create' : 'Update'} failed: {formError}
          </p>
        )}

        <div className="form-actions">
          <button type="submit" disabled={saving}>
            {saving
              ? 'Saving…'
              : form.editingId === null
                ? 'Create goal'
                : 'Save changes'}
          </button>
          {form.editingId !== null && (
            <button type="button" onClick={startCreate}>
              Cancel
            </button>
          )}
        </div>
      </form>
    </section>
  )
}
