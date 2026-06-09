import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()

  const storage: Record<string, string> = {}
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => { storage[key] = value },
    removeItem: (key: string) => { delete storage[key] },
    clear: () => { for (const k of Object.keys(storage)) delete storage[k] },
  })
})

function mockResponse(status: number, data: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

describe('auth service', () => {
  it('login sets access_token in localStorage', async () => {
    const { authService } = await import('@/services/auth')
    mockFetch.mockResolvedValueOnce(mockResponse(200, {
      access_token: 'test-token',
      refresh_token: 'test-refresh',
      token_type: 'bearer',
      expires_in: 3600,
    }))

    const result = await authService.login({ email: 'test@test.com', password: 'pass' })
    expect(result.access_token).toBe('test-token')
    expect(localStorage.getItem('access_token')).toBe('test-token')
  })

  it('register sets access_token', async () => {
    const { authService } = await import('@/services/auth')
    mockFetch.mockResolvedValueOnce(mockResponse(201, {
      access_token: 'reg-token',
      refresh_token: 'reg-refresh',
      token_type: 'bearer',
      expires_in: 3600,
    }))

    const result = await authService.register({ email: 'new@test.com', password: 'password123', name: 'New User' })
    expect(result.access_token).toBe('reg-token')
  })

  it('logout clears tokens', async () => {
    const { authService } = await import('@/services/auth')
    localStorage.setItem('access_token', 'some-token')
    localStorage.setItem('refresh_token', 'some-refresh')
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, headers: new Headers(), json: () => Promise.resolve(null) })

    await authService.logout('some-refresh')
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('me returns user profile', async () => {
    const { authService } = await import('@/services/auth')
    localStorage.setItem('access_token', 'valid-token')
    mockFetch.mockResolvedValueOnce(mockResponse(200, {
      id: '1', email: 'test@test.com', name: 'Test', role: 'user', is_active: true,
    }))

    const user = await authService.me()
    expect(user.email).toBe('test@test.com')
  })

  it('login throws on 401', async () => {
    const { authService } = await import('@/services/auth')
    mockFetch.mockResolvedValueOnce(mockResponse(401, { detail: 'Invalid credentials' }))

    await expect(authService.login({ email: 'bad@test.com', password: 'wrong' }))
      .rejects.toThrow('Invalid credentials')
  })
})
