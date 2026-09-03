import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { Exercise, Goal } from '../api/types'

vi.mock('../api/client', () => ({
  listExercises: vi.fn(),
  listGoals: vi.fn(),
  createGoal: vi.fn(),
  updateGoal: vi.fn(),
  deleteGoal: vi.fn(),
  isApiError: (v: unknown) => v instanceof Error,
}))

import {
  createGoal,
  deleteGoal,
  listExercises,
  listGoals,
  updateGoal,
} from '../api/client'
import Goals from './Goals'

const listExercisesMock = vi.mocked(listExercises)
const listGoalsMock = vi.mocked(listGoals)
const createGoalMock = vi.mocked(createGoal)
const updateGoalMock = vi.mocked(updateGoal)
const deleteGoalMock = vi.mocked(deleteGoal)

const EXERCISES: Exercise[] = [
  {
    id: 1,
    name: 'Bench Press',
    category: 'strength',
    is_preset: true,
    created_at: 'x',
    updated_at: 'x',
  },
  {
    id: 3,
    name: 'Running',
    category: 'cardio',
    is_preset: true,
    created_at: 'x',
    updated_at: 'x',
  },
]

function goal(over: Partial<Goal> & Pick<Goal, 'id' | 'exercise_id' | 'metric' | 'target_value'>): Goal {
  return {
    unit: null,
    description: null,
    created_at: 'x',
    updated_at: 'x',
    ...over,
  }
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <Goals />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  listExercisesMock.mockResolvedValue(EXERCISES)
  listGoalsMock.mockResolvedValue([])
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('renders the goal list from mocked data with exercise name + human target', async () => {
  listGoalsMock.mockImplementation(async (exerciseId: number) => {
    if (exerciseId === 1)
      return [goal({ id: 10, exercise_id: 1, metric: 'weight', target_value: 90, unit: 'kg' })]
    if (exerciseId === 3)
      return [goal({ id: 11, exercise_id: 3, metric: 'distance', target_value: 5000, unit: 'm' })]
    return []
  })
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Goals' })
  expect(within(list).getByText(/Bench Press: target weight 90 kg/)).toBeInTheDocument()
  expect(within(list).getByText(/Running: target distance 5000 m/)).toBeInTheDocument()
})

test('shows an empty state pointing to the form when there are no goals', async () => {
  renderScreen()
  expect(await screen.findByText(/no goals yet/i)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /create a goal/i })).toBeInTheDocument()
})

test('shows an error state with retry when loading fails', async () => {
  listExercisesMock.mockRejectedValueOnce(new Error('down'))
  renderScreen()
  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load your goals/i)
  listExercisesMock.mockResolvedValueOnce(EXERCISES)
  listGoalsMock.mockResolvedValue([])
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(await screen.findByText(/no goals yet/i)).toBeInTheDocument()
})

test('validation blocks save until exercise, metric and a positive target are set', async () => {
  renderScreen()
  await screen.findByText(/no goals yet/i)

  fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))
  expect(screen.getByText('Choose an exercise')).toBeInTheDocument()
  expect(createGoalMock).not.toHaveBeenCalled()

  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Target metric'), { target: { value: 'weight' } })
  fireEvent.change(screen.getByLabelText('Target value'), { target: { value: '-5' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))
  expect(screen.getByText(/positive target value/i)).toBeInTheDocument()
  expect(createGoalMock).not.toHaveBeenCalled()
})

test('creating a goal posts the expected payload and it appears in the list', async () => {
  createGoalMock.mockResolvedValue(
    goal({ id: 20, exercise_id: 1, metric: 'weight', target_value: 100, unit: 'kg', description: 'bench 100 x1' }),
  )
  renderScreen()
  await screen.findByText(/no goals yet/i)

  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Target metric'), { target: { value: 'weight' } })
  fireEvent.change(screen.getByLabelText('Target value'), { target: { value: '100' } })
  fireEvent.change(screen.getByLabelText('Description (optional)'), {
    target: { value: 'bench 100 x1' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))

  await waitFor(() =>
    expect(createGoalMock).toHaveBeenCalledWith(1, {
      metric: 'weight',
      target_value: 100,
      unit: 'kg',
      description: 'bench 100 x1',
    }),
  )
  const list = await screen.findByRole('list', { name: 'Goals' })
  expect(within(list).getByText(/Bench Press: target weight 100 kg \(bench 100 x1\)/)).toBeInTheDocument()
})

test('a failed create shows an error and preserves the entered values', async () => {
  createGoalMock.mockRejectedValue(new Error('server nope'))
  renderScreen()
  await screen.findByText(/no goals yet/i)

  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Target metric'), { target: { value: 'reps' } })
  fireEvent.change(screen.getByLabelText('Target value'), { target: { value: '12' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))

  expect(await screen.findByText(/create failed: server nope/i)).toBeInTheDocument()
  expect((screen.getByLabelText('Target value') as HTMLInputElement).value).toBe('12')
  expect((screen.getByLabelText('Target metric') as HTMLSelectElement).value).toBe('reps')
})

test('editing a goal pre-fills the form and updates the list', async () => {
  listGoalsMock.mockImplementation(async (exerciseId: number) =>
    exerciseId === 1
      ? [goal({ id: 10, exercise_id: 1, metric: 'weight', target_value: 90, unit: 'kg' })]
      : [],
  )
  updateGoalMock.mockResolvedValue(
    goal({ id: 10, exercise_id: 1, metric: 'weight', target_value: 95, unit: 'kg' }),
  )
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Goals' })

  fireEvent.click(within(list).getByRole('button', { name: 'Edit' }))
  expect(screen.getByRole('heading', { name: /edit goal/i })).toBeInTheDocument()
  expect((screen.getByLabelText('Target value') as HTMLInputElement).value).toBe('90')

  fireEvent.change(screen.getByLabelText('Target value'), { target: { value: '95' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

  await waitFor(() =>
    expect(updateGoalMock).toHaveBeenCalledWith(10, {
      metric: 'weight',
      target_value: 95,
      unit: 'kg',
      description: undefined,
    }),
  )
  expect(await within(list).findByText(/target weight 95 kg/)).toBeInTheDocument()
})

test('deleting a goal asks for confirmation then removes it; a failed delete keeps it', async () => {
  listGoalsMock.mockImplementation(async (exerciseId: number) =>
    exerciseId === 1
      ? [goal({ id: 10, exercise_id: 1, metric: 'weight', target_value: 90, unit: 'kg' })]
      : [],
  )
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Goals' })

  // first attempt fails -> goal stays
  deleteGoalMock.mockRejectedValueOnce(new Error('cannot delete'))
  fireEvent.click(within(list).getByRole('button', { name: 'Delete' }))
  expect(window.confirm).toHaveBeenCalled()
  expect(await screen.findByText(/delete failed: cannot delete/i)).toBeInTheDocument()
  expect(within(list).getByText(/target weight 90 kg/)).toBeInTheDocument()

  // second attempt succeeds
  deleteGoalMock.mockResolvedValueOnce(undefined)
  fireEvent.click(within(list).getByRole('button', { name: 'Delete' }))
  await waitFor(() =>
    expect(screen.queryByText(/target weight 90 kg/)).not.toBeInTheDocument(),
  )
})

test('a second goal for the same exercise also appears in the list', async () => {
  listGoalsMock.mockImplementation(async (exerciseId: number) =>
    exerciseId === 1
      ? [goal({ id: 10, exercise_id: 1, metric: 'weight', target_value: 90, unit: 'kg' })]
      : [],
  )
  createGoalMock.mockResolvedValue(
    goal({ id: 21, exercise_id: 1, metric: 'reps', target_value: 10 }),
  )
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Goals' })

  fireEvent.change(screen.getByLabelText('Exercise'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Target metric'), { target: { value: 'reps' } })
  fireEvent.change(screen.getByLabelText('Target value'), { target: { value: '10' } })
  // clear the auto unit for reps
  fireEvent.change(screen.getByLabelText('Unit'), { target: { value: '' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create goal' }))

  await waitFor(() =>
    expect(within(list).getAllByRole('listitem')).toHaveLength(2),
  )
  expect(within(list).getByText(/target weight 90 kg/)).toBeInTheDocument()
  expect(within(list).getByText(/target reps 10/)).toBeInTheDocument()
})
