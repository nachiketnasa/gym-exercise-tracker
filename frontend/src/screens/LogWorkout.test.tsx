import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import type { Exercise, Session } from '../api/types'

vi.mock('../api/client', () => ({
  listExercises: vi.fn(),
  createExercise: vi.fn(),
  createSession: vi.fn(),
  isApiError: (v: unknown) => v instanceof Error,
}))

import { createExercise, createSession, listExercises } from '../api/client'
import LogWorkout from './LogWorkout'

const listExercisesMock = vi.mocked(listExercises)
const createExerciseMock = vi.mocked(createExercise)
const createSessionMock = vi.mocked(createSession)

function exercise(over: Partial<Exercise> & Pick<Exercise, 'id' | 'name' | 'category'>): Exercise {
  return {
    is_preset: true,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    ...over,
  }
}

const EXERCISES: Exercise[] = [
  exercise({ id: 1, name: 'Back Squat', category: 'strength' }),
  exercise({ id: 2, name: 'Bench Press', category: 'strength' }),
  exercise({ id: 3, name: 'Running', category: 'cardio' }),
]

function renderScreen() {
  return render(
    <MemoryRouter>
      <LogWorkout />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  listExercisesMock.mockResolvedValue(EXERCISES)
})

async function selectExercise(name: string | RegExp) {
  const list = await screen.findByRole('list', { name: 'Exercises' })
  fireEvent.click(within(list).getByRole('button', { name: new RegExp(name, 'i') }))
}

test('renders with a mocked exercise list and a date defaulting to today', async () => {
  renderScreen()
  expect(screen.getByRole('status')).toHaveTextContent(/loading exercises/i)
  await screen.findByRole('list', { name: 'Exercises' })
  const dateInput = screen.getByLabelText('Date') as HTMLInputElement
  expect(dateInput.value).toBe(new Date().toISOString().slice(0, 10))
  expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
})

test('shows an error state with retry when the exercise list fails to load', async () => {
  listExercisesMock.mockRejectedValueOnce(new Error('boom'))
  renderScreen()
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent(/could not load exercises/i)
  listExercisesMock.mockResolvedValueOnce(EXERCISES)
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  await screen.findByRole('list', { name: 'Exercises' })
})

test('the exercise picker filters by search text', async () => {
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })
  fireEvent.change(screen.getByLabelText('Search exercises'), {
    target: { value: 'bench' },
  })
  const list = screen.getByRole('list', { name: 'Exercises' })
  expect(within(list).getByRole('button', { name: /bench press/i })).toBeInTheDocument()
  expect(within(list).queryByRole('button', { name: /back squat/i })).not.toBeInTheDocument()
})

test('adds a strength entry and a cardio entry in order', async () => {
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  await selectExercise('back squat')
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '100' } })
  fireEvent.change(screen.getByLabelText('Weight unit'), { target: { value: 'kg' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  await selectExercise('running')
  fireEvent.change(screen.getByLabelText('Duration (seconds)'), { target: { value: '1800' } })
  fireEvent.change(screen.getByLabelText('Distance (meters)'), { target: { value: '5000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  const rows = screen
    .getAllByRole('listitem')
    .filter((li) => li.textContent?.includes('—'))
  expect(rows).toHaveLength(2)
  expect(rows[0]).toHaveTextContent('Back Squat')
  expect(rows[1]).toHaveTextContent('Running')
})

test('creates a custom exercise inline and selects it', async () => {
  createExerciseMock.mockResolvedValue(
    exercise({ id: 99, name: 'Sled Push', category: 'strength', is_preset: false }),
  )
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  fireEvent.click(screen.getByRole('button', { name: 'Add custom exercise' }))
  fireEvent.click(screen.getByRole('button', { name: 'Create & select' }))
  expect(screen.getByRole('alert')).toHaveTextContent(/name is required/i)

  fireEvent.change(screen.getByLabelText('Custom exercise name'), {
    target: { value: 'Sled Push' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Create & select' }))
  expect(screen.getByRole('alert')).toHaveTextContent(/choose a category/i)

  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'strength' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create & select' }))

  await waitFor(() =>
    expect(createExerciseMock).toHaveBeenCalledWith({
      name: 'Sled Push',
      category: 'strength',
    }),
  )
  expect(await screen.findByText(/selected:/i)).toHaveTextContent('Sled Push')
})

test('a backend error on custom creation is surfaced and the session is kept', async () => {
  createExerciseMock.mockRejectedValue(new Error('duplicate name'))
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  // build one entry first
  await selectExercise('bench press')
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '3' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '80' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  fireEvent.click(screen.getByRole('button', { name: 'Add custom exercise' }))
  fireEvent.change(screen.getByLabelText('Custom exercise name'), {
    target: { value: 'Bench Press' },
  })
  fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'strength' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create & select' }))

  await screen.findByText(/duplicate name/i)
  expect(screen.getByText(/Bench Press — 3 reps @ 80 kg/)).toBeInTheDocument()
})

test('validation failure blocks save (negative number rejected)', async () => {
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  // save disabled with no entries
  expect(screen.getByRole('button', { name: 'Save session' })).toBeDisabled()

  await selectExercise('back squat')
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '-5' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '100' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  expect(screen.getByRole('alert')).toHaveTextContent(/reps must be a positive number/i)
  expect(screen.getByRole('button', { name: 'Save session' })).toBeDisabled()
  expect(createSessionMock).not.toHaveBeenCalled()
})

test('a successful save posts the expected payload and resets the form', async () => {
  const saved: Session = { id: 42, date: '2026-08-01', notes: 'leg day', entries: [] }
  createSessionMock.mockResolvedValue(saved)
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-08-01' } })
  fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'leg day' } })

  await selectExercise('back squat')
  fireEvent.change(screen.getByLabelText('Sets'), { target: { value: '3' } })
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '100' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  fireEvent.click(screen.getByRole('button', { name: 'Save session' }))

  await waitFor(() =>
    expect(createSessionMock).toHaveBeenCalledWith({
      date: '2026-08-01',
      notes: 'leg day',
      entries: [
        { exercise_id: 1, reps: 5, weight: 100, weight_unit: 'kg', sets: 3 },
      ],
    }),
  )
  expect(await screen.findByRole('status')).toHaveTextContent(/session saved/i)
  expect(screen.getByText(/no entries yet/i)).toBeInTheDocument()
  expect((screen.getByLabelText('Notes') as HTMLTextAreaElement).value).toBe('')
})

test('a failed save shows an error and preserves the entered session', async () => {
  createSessionMock.mockRejectedValue(new Error('server exploded'))
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })

  fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'keep me' } })
  await selectExercise('bench press')
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '90' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))

  fireEvent.click(screen.getByRole('button', { name: 'Save session' }))

  expect(await screen.findByRole('alert')).toHaveTextContent(/save failed: server exploded/i)
  expect((screen.getByLabelText('Notes') as HTMLTextAreaElement).value).toBe('keep me')
  expect(screen.getByText(/Bench Press — 5 reps @ 90 kg/)).toBeInTheDocument()
})

test('an entry can be removed', async () => {
  renderScreen()
  await screen.findByRole('list', { name: 'Exercises' })
  await selectExercise('back squat')
  fireEvent.change(screen.getByLabelText('Reps'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Weight'), { target: { value: '100' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add entry' }))
  expect(screen.getByText(/Back Squat — 5 reps @ 100 kg/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
  expect(screen.queryByText(/Back Squat — 5 reps/)).not.toBeInTheDocument()
})
