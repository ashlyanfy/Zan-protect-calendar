import { addDays, format, isSameDay, startOfWeek } from 'date-fns'
import { ru } from 'date-fns/locale'
import type { CalendarEvent } from '../types'
import { EVENT_TYPE_META } from '../types'

export default function WeekStrip({
  anchor,
  selectedDay,
  events,
  onSelectDay,
}: {
  anchor: Date
  selectedDay: Date
  events: CalendarEvent[]
  onSelectDay: (day: Date) => void
}) {
  const weekStart = startOfWeek(anchor, { weekStartsOn: 1 })
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const today = new Date()

  return (
    <div className="week-strip">
      {days.map((day) => {
        const dayEvents = events.filter((e) => isSameDay(new Date(e.start_time), day))
        const classes = [
          'week-day',
          isSameDay(day, selectedDay) ? 'selected' : '',
          isSameDay(day, today) ? 'today' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <button key={day.toISOString()} className={classes} onClick={() => onSelectDay(day)}>
            <span className="wd-name">{format(day, 'EEEEEE', { locale: ru })}</span>
            <span className="wd-num">{format(day, 'd')}</span>
            <span className="wd-dots">
              {dayEvents.slice(0, 3).map((e) => (
                <span
                  key={e.id}
                  className="cell-dot"
                  style={{ background: EVENT_TYPE_META[e.event_type].color }}
                />
              ))}
            </span>
          </button>
        )
      })}
    </div>
  )
}
