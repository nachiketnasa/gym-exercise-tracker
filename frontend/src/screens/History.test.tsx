import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'
import type { Paginated, Session, SessionSummary } from '../api/types'

vi.mock('../api/client', () => ({
  listSessions: vi.fn(),
  getSession: vi.fn(),
  listExercises: vi.fn(),
  isApiError: (v: unknown) => v instanceof Error,
}))

import { getSession, listExercises, listSessions } from '../api/client'
import History from './History'

const listSessionsMock = vi.mocked(listSessions)
const getSessionMock = vi.mocked(getSession)
const listExercisesMock = vi.mocked(listExercises)

function summary(id: number, date: string): SessionSummary {
  return { id, date, exercise_count: 2, primary_lifts: ['Back Squat'] }
}

function page(
  items: SessionSummary[],
  pageNum: number,
  total: number,
): Paginated<SessionSummary> {
  return { items, page: pageNum, page_size: 20, total }
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <History />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  listExercisesMock.mockResolvedValue([])
})

test('loads and renders the first page newest-first with date + summary', async () => {
  listSessionsMock.mockResolvedValue(
    page(
      [summary(2, '2026-08-10'), summary(1, '2026-07-01')],
      1,
      2,
    ),
  )
  renderScreen()
  expect(screen.getByRole('status')).toHaveTextContent(/loading history/i)

  const list = await screen.findByRole('list', { name: 'Workout sessions' })
  expect(listSessionsMock).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  const rows = within(list).getAllByRole('listitem')
  expect(rows[0]).toHaveTextContent('August')
  expect(rows[0]).toHaveTextContent('2 exercises')
  expect(rows[0]).toHaveTextContent('Back Squat')
  expect(rows[1]).toHaveTextContent('July')
})

test('shows an error state with retry when the first page fails', async () => {
  listSessionsMock.mockRejectedValueOnce(new Error('nope'))
  renderScreen()
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent(/could not load your history/i)
  listSessionsMock.mockResolvedValueOnce(page([summary(1, '2026-07-01')], 1, 1))
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  await screen.findByRole('list', { name: 'Workout sessions' })
})

test('shows an empty state linking to Log Workout when there is no history', async () => {
  listSessionsMock.mockResolvedValue(page([], 1, 0))
  renderScreen()
  expect(await screen.findByText(/no workout history yet/i)).toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: /log your first workout/i }),
  ).toHaveAttribute('href', '/')
})

test('loads the next page and appends rows without duplicates or reordering', async () => {
  listSessionsMock.mockResolvedValueOnce(
    page([summary(4, '2026-08-04'), summary(3, '2026-08-03')], 1, 4),
  )
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Workout sessions' })
  expect(within(list).getAllByRole('listitem')).toHaveLength(2)

  listSessionsMock.mockResolvedValueOnce(
    page([summary(3, '2026-08-03'), summary(2, '2026-08-02'), summary(1, '2026-08-01')], 2, 4),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))

  await waitFor(() =>
    expect(within(list).getAllByRole('listitem')).toHaveLength(4),
  )
  expect(listSessionsMock).toHaveBeenLastCalledWith({ page: 2, page_size: 20 })
  expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
  expect(screen.getByText(/end of history/i)).toBeInTheDocument()
})

test('a failed subsequent page shows an inline error with retry and keeps rows', async () => {
  listSessionsMock.mockResolvedValueOnce(
    page([summary(3, '2026-08-03'), summary(2, '2026-08-02')], 1, 4),
  )
  renderScreen()
  const list = await screen.findByRole('list', { name: 'Workout sessions' })

  listSessionsMock.mockRejectedValueOnce(new Error('page boom'))
  fireEvent.click(screen.getByRole('button', { name: 'Load more' }))

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent(/could not load more sessions: page boom/i)
  expect(within(list).getAllByRole('listitem')).toHaveLength(2)

  listSessionsMock.mockResolvedValueOnce(
    page([summary(1, '2026-08-01')], 2, 4),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  await waitFor(() =>
    expect(within(list).getAllByRole('listitem')).toHaveLength(3),
  )
})

test('opening a session shows its detail with notes and category-appropriate metrics', async () => {
  listSessionsMock.mockResolvedValue(page([summary(7, '2026-08-10')], 1, 1))
  listExercisesMock.mockResolvedValue([
    {
      id: 1,
      name: 'Back Squat',
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
  ])
  const session: Session = {
    id: 7,
    date: '2026-08-10',
    notes: 'good session',
    entries: [
      { id: 1, exercise_id: 1, position: 0, sets: 3, reps: 5, weight: 100, weight_unit: 'kg' },
      { id: 2, exercise_id: 3, position: 1, duration_seconds: 1800, distance_meters: 5000 },
      { id: 3, exercise_id: 1, position: 2 },
    ],
  }
  getSessionMock.mockResolvedValue(session)

  renderScreen()
  const list = await screen.findByRole('list', { name: 'Workout sessions' })
  fireEvent.click(within(list).getByRole('button'))

  expect(await screen.findByRole('heading', { name: /session detail/i })).toBeInTheDocument()
  await waitFor(() => expect(getSessionMock).toHaveBeenCalledWith(7))
  expect(screen.getByText('good session')).toBeInTheDocument()
  expect(screen.getAllByText('Back Squat').length).toBe(2)
  expect(screen.getByText('Running')).toBeInTheDocument()
  // strength metrics present
  expect(screen.getAllByText('Reps').length).toBeGreaterThan(0)
  // cardio metrics present
  expect(screen.getByText('Distance')).toBeInTheDocument()
  // entry with no metrics renders dashes, no crash
  expect(screen.getAllByText('—').length).toBeGreaterThan(0)

  fireEvent.click(screen.getByRole('button', { name: /back to history/i }))
  expect(await screen.findByRole('list', { name: 'Workout sessions' })).toBeInTheDocument()
})

test('session detail has its own error + retry state', async () => {
  listSessionsMock.mockResolvedValue(page([summary(7, '2026-08-10')], 1, 1))
  getSessionMock.mockRejectedValueOnce(new Error('detail boom'))

  renderScreen()
  const list = await screen.findByRole('list', { name: 'Workout sessions' })
  fireEvent.click(within(list).getByRole('button'))

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent(/could not load this session/i)

  getSessionMock.mockResolvedValueOnce({
    id: 7,
    date: '2026-08-10',
    notes: null,
    entries: [],
  })
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(await screen.findByText(/no exercises recorded/i)).toBeInTheDocument()
})
