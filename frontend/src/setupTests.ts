import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest is not running with `globals: true`, so Testing Library's automatic
// afterEach cleanup never registers. Register it here so each test starts with
// a fresh DOM.
afterEach(() => {
  cleanup()
})
