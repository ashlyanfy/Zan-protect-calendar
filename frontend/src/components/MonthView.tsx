import {
  addDays,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
} from 'date-fns'
import type { CalendarEvent } from '../types'
import { EVENT_TYPE_META } from '../types'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

export default function MonthView({
  month,
  selectedDay,
  events,
  onSelectDay,
}: {
  month: Date
  selectedDay: Date
  events: CalendarEvent[]
  onSelectDay: (day: Date) => void
}) {
  const gridStart = startOfWeek(startOfMonth(month), { weekStartsOn: 1 })
  const gridEnd = endOfWeek(endOfMonth(month), { weekStartsOn: 1 })

  const days: Date[] = []
  for (let d = gridStart; d <= gridEnd; d = addDays(d, 1)) days.push(d)

  const today = new Date()

  return (
    <div className="month-grid">
      <div className="weekday-row">
        {WEEKDAYS.map((w, i) => (
          <span key={w} className={i >= 5 ? 'weekend' : ''}>
            {w}
          </span>
        ))}
      </div>
      <div className="month-cells">
        {days.map((day) => {
          const dayEvents = events.filter((e) => isSameDay(new Date(e.start_time), day))
          const classes = [
            'month-cell',
            !isSameMonth(day, month) ? 'outside' : '',
            isSameDay(day, today) ? 'today' : '',
            isSameDay(day, selectedDay) ? 'selected' : '',
          ]
            .filter(Boolean)
            .join(' ')
          return (
            <div key={day.toISOString()} className={classes} onClick={() => onSelectDay(day)}>
              <span className="cell-day">{format(day, 'd')}</span>
              <div className="cell-dots">
                {dayEvents.slice(0, 4).map((e) => (
                  <span
                    key={e.id}
                    className="cell-dot"
                    style={{ background: EVENT_TYPE_META[e.event_type].color }}
                  />
                ))}
              </div>
              {dayEvents.slice(0, 2).map((e) => {
                const meta = EVENT_TYPE_META[e.event_type]
                return (
                  <span key={e.id} className="cell-chip" style={{ color: meta.color, background: meta.bg }}>
                    {e.title}
                  </span>
                )
              })}
              {dayEvents.length > 2 && <span className="cell-more">ещё {dayEvents.length - 2}</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
