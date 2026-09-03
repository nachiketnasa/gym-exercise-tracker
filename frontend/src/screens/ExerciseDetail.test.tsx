import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import type {
  Exercise,
  Goal,
  PersonalRecord,
  ProgressPoint,
} from '../api/types'

vi.mock('recharts', () => ({
  LineChart: ({ children }: { children?: unknown }) => (
    <div data-testid="linechart">{children as never}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

vi.mock('../api/client', () => ({
  getExercise: vi.fn(),
  getExerciseProgress: vi.fn(),
  getExercisePersonalRecords: vi.fn(),
  listGoals: vi.fn(),
  isApiError: (v: unknown) => v instanceof Error,
}))

import {
  getExercise,
  getExercisePersonalRecords,
  getExerciseProgress,
  listGoals,
} from '../api/client'
import ExerciseDetail from './ExerciseDetail'

const getExerciseMock = vi.mocked(getExercise)
const getProgressMock = vi.mocked(getExerciseProgress)
const getPrsMock = vi.mocked(getExercisePersonalRecords)
const listGoalsMock = vi.mocked(listGoals)

const SQUAT: Exercise = {
  id: 5,
  name: 'Back Squat',
  category: 'strength',
  is_preset: true,
  created_at: 'x',
  updated_at: 'x',
}

const PROGRESS: ProgressPoint[] = [
  { date: '2026-07-01', value: 100 },
  { date: '2026-08-01', value: 110 },
]

const PRS: PersonalRecord[] = [
  { metric: 'weight', value: 120, achieved_on: '2026-08-01', session_id: 1, entry_id: 2 },
]

const GOALS: Goal[] = [
  {
    id: 9,
    exercise_id: 5,
    metric: 'weight',
    target_value: 140,
    unit: 'kg',
    description: null,
    created_at: 'x',
    updated_at: 'x',
  },
]

function renderAt(id = '5') {
  return render(
    <MemoryRouter initialEntries={[`/exercises/${id}`]}>
      <Routes>
        <Route path="/exercises/:exerciseId" element={<ExerciseDetail />} />
        <Route path="/goals" element={<div>Goals screen</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  getExerciseMock.mockResolvedValue(SQUAT)
  getProgressMock.mockResolvedValue(PROGRESS)
  getPrsMock.mockResolvedValue(PRS)
  listGoalsMock.mockResolvedValue(GOALS)
})

test('renders exercise header and all three sections from mocked data', async () => {
  renderAt()
  expect(await screen.findByRole('heading', { name: 'Back Squat' })).toBeInTheDocument()
  expect(screen.getByText(/category: strength/i)).toBeInTheDocument()

  expect(await screen.findByTestId('progress-chart')).toBeInTheDocument()
  expect(screen.getByText(/weight \(kg\) over time/i)).toBeInTheDocument()

  const prSection = await screen.findByRole('region', { name: /personal records/i })
  expect(
    await within(prSection).findByText(/weight: 120 kg \(achieved 2026-08-01\)/i),
  ).toBeInTheDocument()

  const goalSection = await screen.findByRole('region', { name: /^goals$/i })
  expect(await within(goalSection).findByText(/target weight 140 kg/i)).toBeInTheDocument()
  expect(within(goalSection).getByRole('link', { name: /add or edit goals/i })).toBeInTheDocument()

  expect(getProgressMock).toHaveBeenCalledWith(5, { metric: 'weight' })
  expect(getPrsMock).toHaveBeenCalledWith(5)
  expect(listGoalsMock).toHaveBeenCalledWith(5)
})

test('switching the metric re-fetches progress and updates the chart caption', async () => {
  renderAt()
  await screen.findByTestId('progress-chart')
  expect(getProgressMock).toHaveBeenCalledWith(5, { metric: 'weight' })

  getProgressMock.mockResolvedValueOnce([{ date: '2026-07-01', value: 5 }])
  fireEvent.change(screen.getByLabelText('Metric'), { target: { value: 'reps' } })

  await waitFor(() =>
    expect(getProgressMock).toHaveBeenLastCalledWith(5, { metric: 'reps' }),
  )
  expect(await screen.findByText(/^reps over time$/i)).toBeInTheDocument()
})

test('shows the no-data empty state for a metric with no points', async () => {
  getProgressMock.mockResolvedValue([])
  renderAt()
  expect(
    await screen.findByText(/no data logged for this metric yet/i),
  ).toBeInTheDocument()
  expect(screen.queryByTestId('progress-chart')).not.toBeInTheDocument()
})

test('renders the chart with a single data point without error', async () => {
  getProgressMock.mockResolvedValue([{ date: '2026-07-01', value: 100 }])
  renderAt()
  expect(await screen.findByTestId('progress-chart')).toBeInTheDocument()
})

test('shows empty PR and empty goal states', async () => {
  getPrsMock.mockResolvedValue([])
  listGoalsMock.mockResolvedValue([])
  renderAt()
  expect(await screen.findByText(/no personal records yet/i)).toBeInTheDocument()
  const goalSection = await screen.findByRole('region', { name: /^goals$/i })
  expect(within(goalSection).getByText(/no active goals for this exercise/i)).toBeInTheDocument()
  expect(within(goalSection).getByRole('link', { name: /add or edit goals/i })).toBeInTheDocument()
})

test('one section can error and retry independently of the others', async () => {
  getPrsMock.mockRejectedValueOnce(new Error('pr boom'))
  renderAt()

  const prSection = await screen.findByRole('region', { name: /personal records/i })
  expect(await within(prSection).findByRole('alert')).toHaveTextContent(
    /could not load personal records/i,
  )
  // other sections still fine
  expect(await screen.findByTestId('progress-chart')).toBeInTheDocument()

  getPrsMock.mockResolvedValueOnce(PRS)
  fireEvent.click(within(prSection).getByRole('button', { name: 'Retry' }))
  expect(await within(prSection).findByText(/weight: 120 kg/i)).toBeInTheDocument()
})

test('an unknown exercise id shows a not-found state', async () => {
  getExerciseMock.mockRejectedValueOnce(
    Object.assign(new Error('not found'), { status: 404 }),
  )
  renderAt('999')
  expect(
    await screen.findByRole('heading', { name: /exercise not found/i }),
  ).toBeInTheDocument()
  expect(getProgressMock).not.toHaveBeenCalled()
})
