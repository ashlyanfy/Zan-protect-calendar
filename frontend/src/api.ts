import type { CalendarEvent, EventPayload, User } from './types'

const TOKEN_KEY = 'zanprotect-token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* localStorage недоступен */
  }
}

export class UnauthorizedError extends Error {}

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> | undefined),
  }
  if (init.body) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, { ...init, headers })

  if (res.status === 401) {
    setToken(null)
    throw new UnauthorizedError('Требуется вход в систему')
  }
  if (!res.ok) {
    let detail = `Ошибка ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: any) => d.msg).join('; ')
    } catch {
      /* оставляем detail по умолчанию */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ---------- Авторизация ----------

export async function login(loginName: string, password: string): Promise<{ token: string; user: User }> {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login: loginName, password }),
  })
}

export async function fetchMe(): Promise<User> {
  return request('/api/auth/me')
}

/** Смена собственных логина, имени и пароля. Возвращает новый токен. */
export async function updateCredentials(payload: {
  current_password: string
  login?: string
  name?: string
  password?: string
}): Promise<{ token: string; user: User }> {
  return request('/api/auth/credentials', { method: 'PATCH', body: JSON.stringify(payload) })
}

// ---------- Сотрудники (только админ) ----------

export async function fetchUsers(): Promise<User[]> {
  return request('/api/users')
}

export async function createUser(payload: { login: string; password: string; name: string }): Promise<User> {
  return request('/api/users', { method: 'POST', body: JSON.stringify(payload) })
}

export async function updateUser(
  id: string,
  payload: { login?: string; name?: string; password?: string },
): Promise<User> {
  return request(`/api/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export async function deleteUser(id: string): Promise<void> {
  return request(`/api/users/${id}`, { method: 'DELETE' })
}

// ---------- События ----------

/** userId — чей календарь запрашиваем (доступно только администратору). */
export async function fetchEvents(start?: Date, end?: Date, userId?: string | null): Promise<CalendarEvent[]> {
  const params = new URLSearchParams()
  if (start) params.set('start', start.toISOString())
  if (end) params.set('end', end.toISOString())
  if (userId) params.set('user_id', userId)
  const qs = params.toString()
  return request(qs ? `/api/events?${qs}` : '/api/events')
}

export async function createEvent(payload: EventPayload, userId?: string | null): Promise<CalendarEvent> {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  return request(`/api/events${qs}`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function updateEvent(id: string, payload: EventPayload): Promise<CalendarEvent> {
  return request(`/api/events/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
}

export async function deleteEvent(id: string): Promise<void> {
  return request(`/api/events/${id}`, { method: 'DELETE' })
}
