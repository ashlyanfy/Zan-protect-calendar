import type { CalendarEvent } from '../types'
import { EVENT_TYPE_META, REMINDER_OPTIONS } from '../types'

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export default function EventCard({
  event,
  onClick,
}: {
  event: CalendarEvent
  onClick: () => void
}) {
  const meta = EVENT_TYPE_META[event.event_type]
  const reminderLabel =
    event.reminder_minutes != null
      ? REMINDER_OPTIONS.find((o) => o.value === event.reminder_minutes)?.label?.toLowerCase()
      : null

  return (
    <div className="event-card" style={{ borderLeftColor: meta.color }} onClick={onClick}>
      <div className="event-time">
        <span className="t-start">{fmtTime(event.start_time)}</span>
        {event.end_time && <span className="t-end">{fmtTime(event.end_time)}</span>}
      </div>
      <div className="event-info">
        <div className="event-title">{event.title}</div>
        <div className="event-meta">
          <span className="type-badge" style={{ color: meta.color, background: meta.bg }}>
            {meta.label}
          </span>
          {event.case_number && <span className="event-sub">Дело {event.case_number}</span>}
          {reminderLabel && <span className="event-bell">🔔 {reminderLabel}</span>}
        </div>
        {event.location && <div className="event-meta"><span className="event-sub">📍 {event.location}</span></div>}
      </div>
    </div>
  )
}
