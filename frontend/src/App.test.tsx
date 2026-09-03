import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'
import App from './App'

// The screens fetch through the api client; stub it so routing tests never
// touch the network. getExercise rejects with a 404 so the Exercise Detail
// route lands on its not-found state (which still proves the route + param
// resolved).
vi.mock('./api/client', () => ({
  listExercises: vi.fn().mockResolvedValue([]),
  listSessions: vi.fn().mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 }),
  listGoals: vi.fn().mockResolvedValue([]),
  getExercise: vi.fn().mockRejectedValue(Object.assign(new Error('not found'), { status: 404 })),
  getExercisePersonalRecords: vi.fn().mockResolvedValue([]),
  getExerciseProgress: vi.fn().mockResolvedValue([]),
  isApiError: (v: unknown) => v instanceof Error,
}))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

test('renders the Log Workout screen at /', () => {
  renderAt('/')
  expect(
    screen.getByRole('heading', { name: 'Log Workout' }),
  ).toBeInTheDocument()
})

test('activating a nav item changes the visible screen', () => {
  renderAt('/')
  expect(
    screen.getByRole('heading', { name: 'Log Workout' }),
  ).toBeInTheDocument()

  fireEvent.click(screen.getByRole('link', { name: 'History' }))

  expect(screen.getByRole('heading', { name: 'History' })).toBeInTheDocument()
  expect(
    screen.queryByRole('heading', { name: 'Log Workout' }),
  ).not.toBeInTheDocument()
})

test('deep-linking to /goals renders the Goals screen', () => {
  renderAt('/goals')
  expect(screen.getByRole('heading', { name: 'Goals' })).toBeInTheDocument()
})

test('the /exercises/:exerciseId route reads and shows the param', async () => {
  renderAt('/exercises/123')
  // ExerciseDetail resolves the :exerciseId param and renders it
  expect(await screen.findByText(/id 123/i)).toBeInTheDocument()
})

test('an unknown route renders the Not Found screen inside the layout', () => {
  renderAt('/nonsense')
  expect(screen.getByRole('heading', { name: 'Not Found' })).toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument()
})

test('the active nav item is marked with aria-current="page"', () => {
  renderAt('/')
  fireEvent.click(screen.getByRole('link', { name: 'History' }))
  expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  expect(screen.getByRole('link', { name: 'Log Workout' })).not.toHaveAttribute(
    'aria-current',
  )
})
