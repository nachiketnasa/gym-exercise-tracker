import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import {
  ApiError,
  API_BASE_URL,
  createExercise,
  deleteGoal,
  getExercise,
  getExerciseProgress,
  isApiError,
  listExercises,
  listSessions,
  toQueryString,
} from './client'

/** Build a `Response`-like object for the mocked fetch. */
function mockResponse(
  body: unknown,
  init: { status?: number; ok?: boolean } = {},
): Response {
  const status = init.status ?? 200
  const text = body === undefined ? '' : JSON.stringify(body)
  return {
    ok: init.ok ?? (status >= 200 && status < 300),
    status,
    text: () => Promise.resolve(text),
  } as Response
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('success path', () => {
  test('resolves with the parsed JSON body', async () => {
    const exercises = [
      {
        id: 1,
        name: 'Bench Press',
        category: 'strength',
        is_preset: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]
    fetchMock.mockResolvedValue(mockResponse(exercises))

    await expect(listExercises()).resolves.toEqual(exercises)
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/exercises`, {
      method: 'GET',
    })
  })

  test('a GET request sends no body and no Content-Type header', async () => {
    fetchMock.mockResolvedValue(mockResponse([]))

    await listExercises()

    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('GET')
    expect(init.body).toBeUndefined()
    expect(init.headers).toBeUndefined()
  })

  test('a request with a body sends Content-Type: application/json', async () => {
    fetchMock.mockResolvedValue(
      mockResponse({ id: 9 }, { status: 201 }),
    )

    await createExercise({ name: 'Zercher Squat', category: 'strength' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_BASE_URL}/exercises`)
    expect(init.method).toBe('POST')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init.body)).toEqual({
      name: 'Zercher Squat',
      category: 'strength',
    })
  })
})

describe('HTTP error path', () => {
  test('a non-2xx response rejects with a typed ApiError carrying status + envelope', async () => {
    const envelope = { error: { message: 'Name already taken', code: 'conflict' } }
    fetchMock.mockResolvedValue(mockResponse(envelope, { status: 409 }))

    const err = await createExercise({
      name: 'Bench Press',
      category: 'strength',
    }).catch((e: unknown) => e)

    expect(isApiError(err)).toBe(true)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).kind).toBe('http')
    expect((err as ApiError).status).toBe(409)
    expect((err as ApiError).body).toEqual(envelope)
    expect((err as ApiError).message).toBe('Name already taken')
  })

  test('a 404 rejects with an ApiError whose status is 404', async () => {
    fetchMock.mockResolvedValue(
      mockResponse({ detail: 'Not Found' }, { status: 404 }),
    )

    const err = await getExercise(999).catch((e: unknown) => e)

    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).kind).toBe('http')
    expect((err as ApiError).status).toBe(404)
    // Falls back to FastAPI's `{ detail }` shape when the #15 envelope is absent.
    expect((err as ApiError).message).toBe('Not Found')
  })
})

describe('network error path', () => {
  test('a rejected fetch surfaces as an ApiError flagged "network"', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const err = await listExercises().catch((e: unknown) => e)

    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).kind).toBe('network')
    expect((err as ApiError).status).toBeUndefined()
    expect((err as ApiError).cause).toBeInstanceOf(TypeError)
  })
})

describe('empty body', () => {
  test('a 204 response resolves without a JSON parse error', async () => {
    fetchMock.mockResolvedValue(mockResponse(undefined, { status: 204 }))

    await expect(deleteGoal(3)).resolves.toBeUndefined()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_BASE_URL}/goals/3`)
    expect(init.method).toBe('DELETE')
  })
})

describe('query serialization', () => {
  test('toQueryString skips undefined/null and returns "" when empty', () => {
    expect(toQueryString()).toBe('')
    expect(toQueryString({ a: undefined, b: null })).toBe('')
    expect(toQueryString({ page: 2, q: 'x' })).toBe('?page=2&q=x')
  })

  test('listSessions serializes pagination + date range into the URL', async () => {
    fetchMock.mockResolvedValue(
      mockResponse({ items: [], page: 2, page_size: 10, total: 0 }),
    )

    await listSessions({
      page: 2,
      page_size: 10,
      start_date: '2026-01-01',
      end_date: '2026-03-01',
    })

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/sessions?page=2&page_size=10&start_date=2026-01-01&end_date=2026-03-01`,
      { method: 'GET' },
    )
  })

  test('getExerciseProgress serializes the metric selection', async () => {
    fetchMock.mockResolvedValue(mockResponse([]))

    await getExerciseProgress(5, { metric: 'weight', start_date: '2026-01-01' })

    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe(
      `${API_BASE_URL}/exercises/5/progress?metric=weight&start_date=2026-01-01`,
    )
  })
})
