import type { CalendarEvent } from './types'
import { EVENT_TYPE_META } from './types'

const NOTIFIED_KEY = 'zanprotect-notified'

function getNotified(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(NOTIFIED_KEY) ?? '{}')
  } catch {
    return {}
  }
}

function saveNotified(map: Record<string, number>) {
  try {
    localStorage.setItem(NOTIFIED_KEY, JSON.stringify(map))
  } catch {
    /* localStorage недоступен — просто не сохраняем */
  }
}

export async function ensureNotificationPermission(): Promise<boolean> {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  const result = await Notification.requestPermission()
  return result === 'granted'
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

/** Проверяет события и показывает уведомления для тех, у кого настало время напоминания. */
export function checkReminders(events: CalendarEvent[]) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return

  const now = Date.now()
  const notified = getNotified()

  // чистим записи старше 30 дней
  for (const [id, ts] of Object.entries(notified)) {
    if (now - ts > 30 * 24 * 60 * 60 * 1000) delete notified[id]
  }

  for (const ev of events) {
    if (ev.reminder_minutes == null) continue
    const start = new Date(ev.start_time).getTime()
    const remindAt = start - ev.reminder_minutes * 60 * 1000
    // показываем, если время напоминания настало, но событие ещё не началось (+5 мин допуск)
    if (now >= remindAt && now < start + 5 * 60 * 1000 && !notified[ev.id]) {
      const meta = EVENT_TYPE_META[ev.event_type]
      const body = [
        `${meta.label} в ${formatTime(ev.start_time)}`,
        ev.location ? `Место: ${ev.location}` : null,
        ev.case_number ? `Дело: ${ev.case_number}` : null,
      ]
        .filter(Boolean)
        .join('\n')
      try {
        new Notification(ev.title, { body, icon: '/icons/icon-192.png', tag: ev.id })
      } catch {
        /* некоторые платформы требуют показа через SW — молча пропускаем */
      }
      notified[ev.id] = now
    }
  }
  saveNotified(notified)
}
