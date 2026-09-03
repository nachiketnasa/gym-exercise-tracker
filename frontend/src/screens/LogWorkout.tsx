import { useEffect, useState } from 'react'
import {
  createExercise,
  createSession,
  isApiError,
  listExercises,
} from '../api/client'
import type {
  CreateSessionEntryInput,
  Exercise,
  ExerciseCategory,
} from '../api/types'
import './LogWorkout.css'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function errorMessage(err: unknown): string {
  if (isApiError(err)) return err.message
  return err instanceof Error ? err.message : 'Something went wrong'
}

/** A positive-number parse: returns the number, or null if blank/invalid/negative. */
function positive(value: string): number | null {
  if (value.trim() === '') return null
  const n = Number(value)
  if (!Number.isFinite(n) || n <= 0) return null
  return n
}

interface DraftEntry {
  key: number
  exercise: Exercise
  metrics: CreateSessionEntryInput
  summary: string
}

let keySeq = 1

export default function LogWorkout() {
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'error' | 'ready'>(
    'loading',
  )

  const [date, setDate] = useState(today)
  const [notes, setNotes] = useState('')
  const [entries, setEntries] = useState<DraftEntry[]>([])

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<number | null>(null)

  const [loadNonce, setLoadNonce] = useState(0)
  function retryLoad() {
    setLoadStatus('loading')
    setExercises([])
    setLoadNonce((n) => n + 1)
  }

  useEffect(() => {
    let active = true
    listExercises()
      .then((list) => {
        if (!active) return
        setExercises(list)
        setLoadStatus('ready')
      })
      .catch(() => {
        if (active) setLoadStatus('error')
      })
    return () => {
      active = false
    }
  }, [loadNonce])

  function addEntry(entry: DraftEntry) {
    setEntries((prev) => [...prev, entry])
    setSavedId(null)
  }

  function removeEntry(key: number) {
    setEntries((prev) => prev.filter((e) => e.key !== key))
  }

  function addCustomExercise(name: string, category: ExerciseCategory) {
    return createExercise({ name, category }).then((created) => {
      setExercises((prev) =>
        prev.some((e) => e.id === created.id) ? prev : [...prev, created],
      )
      return created
    })
  }

  function save() {
    setSaving(true)
    setSaveError(null)
    createSession({
      date,
      notes: notes.trim() ? notes.trim() : undefined,
      entries: entries.map((e) => e.metrics),
    })
      .then((session) => {
        setSavedId(session.id)
        setDate(today())
        setNotes('')
        setEntries([])
      })
      .catch((err) => setSaveError(errorMessage(err)))
      .finally(() => setSaving(false))
  }

  const canSave = entries.length > 0 && !saving

  return (
    <section className="log-workout">
      <h1>Log Workout</h1>

      <label className="field">
        <span>Date</span>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </label>

      <label className="field">
        <span>Notes</span>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional session notes"
        />
      </label>

      <h2>Entries</h2>
      {entries.length === 0 ? (
        <p>No entries yet. Add an exercise below.</p>
      ) : (
        <ol className="entry-list">
          {entries.map((entry) => (
            <li key={entry.key}>
              <span>
                {entry.exercise.name} — {entry.summary}
              </span>
              <button type="button" onClick={() => removeEntry(entry.key)}>
                Remove
              </button>
            </li>
          ))}
        </ol>
      )}

      <EntryBuilder
        loadStatus={loadStatus}
        exercises={exercises}
        onRetryLoad={retryLoad}
        onAddCustomExercise={addCustomExercise}
        onAddEntry={addEntry}
      />

      <div className="save-bar">
        <button type="button" onClick={save} disabled={!canSave}>
          {saving ? 'Saving…' : 'Save session'}
        </button>
        {entries.length === 0 && (
          <p className="hint">Add at least one entry to save.</p>
        )}
        {saveError && (
          <p role="alert" className="error">
            Save failed: {saveError}
          </p>
        )}
        {savedId !== null && (
          <p role="status" className="ok">
            Session saved. Started a new empty session.
          </p>
        )}
      </div>
    </section>
  )
}

interface EntryBuilderProps {
  loadStatus: 'loading' | 'error' | 'ready'
  exercises: Exercise[]
  onRetryLoad: () => void
  onAddCustomExercise: (
    name: string,
    category: ExerciseCategory,
  ) => Promise<Exercise>
  onAddEntry: (entry: DraftEntry) => void
}

function EntryBuilder({
  loadStatus,
  exercises,
  onRetryLoad,
  onAddCustomExercise,
  onAddEntry,
}: EntryBuilderProps) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Exercise | null>(null)

  // metric inputs (strings so validation can catch non-numeric)
  const [sets, setSets] = useState('')
  const [reps, setReps] = useState('')
  const [weight, setWeight] = useState('')
  const [weightUnit, setWeightUnit] = useState<'kg' | 'lb'>('kg')
  const [duration, setDuration] = useState('')
  const [distance, setDistance] = useState('')
  const [pace, setPace] = useState('')
  const [metricError, setMetricError] = useState<string | null>(null)

  // inline custom exercise
  const [showCustom, setShowCustom] = useState(false)
  const [customName, setCustomName] = useState('')
  const [customCategory, setCustomCategory] = useState<ExerciseCategory | ''>('')
  const [customError, setCustomError] = useState<string | null>(null)
  const [creatingCustom, setCreatingCustom] = useState(false)

  function resetMetrics() {
    setSets('')
    setReps('')
    setWeight('')
    setDuration('')
    setDistance('')
    setPace('')
    setMetricError(null)
  }

  function pick(exercise: Exercise) {
    setSelected(exercise)
    resetMetrics()
  }

  function submitCustom() {
    if (customName.trim() === '') {
      setCustomError('Name is required')
      return
    }
    if (customCategory === '') {
      setCustomError('Choose a category')
      return
    }
    setCustomError(null)
    setCreatingCustom(true)
    onAddCustomExercise(customName.trim(), customCategory)
      .then((created) => {
        pick(created)
        setShowCustom(false)
        setCustomName('')
        setCustomCategory('')
      })
      .catch((err) => setCustomError(errorMessage(err)))
      .finally(() => setCreatingCustom(false))
  }

  function addEntry() {
    if (!selected) return
    if (selected.category === 'strength') {
      const r = positive(reps)
      const w = positive(weight)
      if (reps.trim() !== '' && r === null) {
        setMetricError('Reps must be a positive number')
        return
      }
      if (weight.trim() !== '' && w === null) {
        setMetricError('Weight must be a positive number')
        return
      }
      if (sets.trim() !== '' && positive(sets) === null) {
        setMetricError('Sets must be a positive number')
        return
      }
      if (r === null || w === null) {
        setMetricError('Reps and weight are required')
        return
      }
      const metrics: CreateSessionEntryInput = {
        exercise_id: selected.id,
        reps: r,
        weight: w,
        weight_unit: weightUnit,
      }
      const s = positive(sets)
      if (s !== null) metrics.sets = s
      onAddEntry({
        key: keySeq++,
        exercise: selected,
        metrics,
        summary: `${s ? `${s} × ` : ''}${r} reps @ ${w} ${weightUnit}`,
      })
    } else {
      const d = positive(duration)
      const dist = positive(distance)
      if (duration.trim() !== '' && d === null) {
        setMetricError('Duration must be a positive number')
        return
      }
      if (distance.trim() !== '' && dist === null) {
        setMetricError('Distance must be a positive number')
        return
      }
      if (pace.trim() !== '' && positive(pace) === null) {
        setMetricError('Pace must be a positive number')
        return
      }
      if (d === null || dist === null) {
        setMetricError('Duration and distance are required')
        return
      }
      const metrics: CreateSessionEntryInput = {
        exercise_id: selected.id,
        duration_seconds: d,
        distance_meters: dist,
      }
      const p = positive(pace)
      if (p !== null) metrics.pace_seconds_per_km = p
      onAddEntry({
        key: keySeq++,
        exercise: selected,
        metrics,
        summary: `${dist} m in ${d} s`,
      })
    }
    setSelected(null)
    resetMetrics()
    setSearch('')
  }

  if (loadStatus === 'loading') {
    return <p role="status">Loading exercises…</p>
  }
  if (loadStatus === 'error') {
    return (
      <div role="alert">
        <p>Could not load exercises.</p>
        <button type="button" onClick={onRetryLoad}>
          Retry
        </button>
      </div>
    )
  }

  const filtered = exercises.filter((e) =>
    e.name.toLowerCase().includes(search.trim().toLowerCase()),
  )

  return (
    <div className="entry-builder">
      <h3>Add an exercise</h3>

      {!selected && (
        <>
          <label className="field">
            <span>Search exercises</span>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter…"
            />
          </label>
          <ul className="exercise-list" aria-label="Exercises">
            {filtered.map((exercise) => (
              <li key={exercise.id}>
                <button type="button" onClick={() => pick(exercise)}>
                  {exercise.name} ({exercise.category})
                </button>
              </li>
            ))}
            {filtered.length === 0 && <li>No matching exercises</li>}
          </ul>

          <button type="button" onClick={() => setShowCustom((v) => !v)}>
            {showCustom ? 'Cancel custom exercise' : 'Add custom exercise'}
          </button>

          {showCustom && (
            <div className="custom-exercise">
              <label className="field">
                <span>Custom exercise name</span>
                <input
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Category</span>
                <select
                  value={customCategory}
                  onChange={(e) =>
                    setCustomCategory(e.target.value as ExerciseCategory | '')
                  }
                >
                  <option value="">Choose…</option>
                  <option value="strength">strength</option>
                  <option value="cardio">cardio</option>
                </select>
              </label>
              {customError && (
                <p role="alert" className="error">
                  {customError}
                </p>
              )}
              <button
                type="button"
                onClick={submitCustom}
                disabled={creatingCustom}
              >
                {creatingCustom ? 'Creating…' : 'Create & select'}
              </button>
            </div>
          )}
        </>
      )}

      {selected && (
        <div className="metric-inputs">
          <p>
            Selected: <strong>{selected.name}</strong> ({selected.category}){' '}
            <button type="button" onClick={() => setSelected(null)}>
              Change
            </button>
          </p>

          {selected.category === 'strength' ? (
            <>
              <label className="field">
                <span>Sets</span>
                <input
                  type="number"
                  value={sets}
                  onChange={(e) => setSets(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Reps</span>
                <input
                  type="number"
                  value={reps}
                  onChange={(e) => setReps(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Weight</span>
                <input
                  type="number"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Weight unit</span>
                <select
                  value={weightUnit}
                  onChange={(e) =>
                    setWeightUnit(e.target.value as 'kg' | 'lb')
                  }
                >
                  <option value="kg">kg</option>
                  <option value="lb">lb</option>
                </select>
              </label>
            </>
          ) : (
            <>
              <label className="field">
                <span>Duration (seconds)</span>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Distance (meters)</span>
                <input
                  type="number"
                  value={distance}
                  onChange={(e) => setDistance(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Pace (seconds per km)</span>
                <input
                  type="number"
                  value={pace}
                  onChange={(e) => setPace(e.target.value)}
                />
              </label>
            </>
          )}

          {metricError && (
            <p role="alert" className="error">
              {metricError}
            </p>
          )}
          <button type="button" onClick={addEntry}>
            Add entry
          </button>
        </div>
      )}
    </div>
  )
}
