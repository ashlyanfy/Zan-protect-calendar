import type { CalendarEvent, EventPayload } from './types'

const BASE = '/api/events'

async function handle<T>(res: Response): Promise<T> {
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

export async function fetchEvents(start?: Date, end?: Date): Promise<CalendarEvent[]> {
  const params = new URLSearchParams()
  if (start) params.set('start', start.toISOString())
  if (end) params.set('end', end.toISOString())
  const qs = params.toString()
  return handle(await fetch(qs ? `${BASE}?${qs}` : BASE))
}

export async function createEvent(payload: EventPayload): Promise<CalendarEvent> {
  return handle(
    await fetch(BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
}

export async function updateEvent(id: string, payload: EventPayload): Promise<CalendarEvent> {
  return handle(
    await fetch(`${BASE}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
}

export async function deleteEvent(id: string): Promise<void> {
  return handle(await fetch(`${BASE}/${id}`, { method: 'DELETE' }))
}
