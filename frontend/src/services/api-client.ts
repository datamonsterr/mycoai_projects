const API_BASE = '/api/v1'

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
  params?: Record<string, string | number | boolean | undefined>
}

class ApiError extends Error {
  status: number
  detail: Record<string, unknown> | null

  constructor(status: number, detail: string | Record<string, unknown> | null) {
    const message = typeof detail === 'string' ? detail : (detail as Record<string, string>)?.detail ?? 'Request failed'
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = typeof detail === 'object' ? detail as Record<string, unknown> : null
  }

  get isUnauthorized() { return this.status === 401 }
  get isForbidden() { return this.status === 403 }
  get isNotFound() { return this.status === 404 }
  get isConflict() { return this.status === 409 }
  get isValidationError() { return this.status === 422 }
  get isServerError() { return this.status >= 500 }
}

function getToken(): string | null {
  try {
    return localStorage.getItem('access_token')
  } catch {
    return null
  }
}

function getRefreshToken(): string | null {
  try {
    return localStorage.getItem('refresh_token')
  } catch {
    return null
  }
}

export function setToken(token: string) {
  localStorage.setItem('access_token', token)
}

export function clearToken() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

let refreshPromise: Promise<string | null> | null = null

async function tryRefreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise

  const rt = getRefreshToken()
  if (!rt) return null

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      if (!res.ok) {
        clearToken()
        return null
      }
      const data = await res.json() as { access_token: string; refresh_token?: string }
      setToken(data.access_token)
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      return data.access_token
    } catch {
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, headers: initHeaders, ...init } = options

  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v))
    })
  }

  const buildHeaders = (token: string | null): HeadersInit => {
    const h: HeadersInit = { ...initHeaders as Record<string, string> }
    if (token) {
      (h as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }
    if (body && !(body instanceof FormData)) {
      (h as Record<string, string>)['Content-Type'] = 'application/json'
    }
    return h
  }

  const doFetch = async (token: string | null) => {
    const headers = buildHeaders(token)
    const res = await fetch(url.toString(), {
      ...init,
      headers,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    })
    return res
  }

  let res = await doFetch(getToken())

  if (res.status === 401 && getRefreshToken() && path !== '/auth/refresh' && path !== '/auth/login') {
    const newToken = await tryRefreshToken()
    if (newToken) {
      res = await doFetch(newToken)
    }
  }

  if (res.status === 204) {
    return undefined as T
  }

  let data: unknown
  const contentType = res.headers.get('content-type')
  if (contentType?.includes('application/json')) {
    data = await res.json()
  } else {
    data = await res.text()
  }

  if (!res.ok) {
    throw new ApiError(res.status, data as Record<string, unknown> | string)
  }

  return data as T
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T = void>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'DELETE' }),
}

export { ApiError, request }
export type { RequestOptions }
