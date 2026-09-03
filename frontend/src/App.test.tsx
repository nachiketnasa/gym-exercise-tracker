import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import App from './App'

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

test('the /exercises/:exerciseId route reads and shows the param', () => {
  renderAt('/exercises/123')
  expect(
    screen.getByRole('heading', { name: 'Exercise Detail' }),
  ).toBeInTheDocument()
  expect(screen.getByText(/123/)).toBeInTheDocument()
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
