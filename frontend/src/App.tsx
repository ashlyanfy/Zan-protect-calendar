import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  addDays,
  addMonths,
  addWeeks,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  startOfMonth,
  startOfWeek,
  subMonths,
  subWeeks,
} from 'date-fns'
import { ru } from 'date-fns/locale'
import { createEvent, deleteEvent, fetchEvents, updateEvent } from './api'
import MonthView from './components/MonthView'
import WeekStrip from './components/WeekStrip'
import EventCard from './components/EventCard'
import EventModal from './components/EventModal'
import { checkReminders, ensureNotificationPermission } from './notifications'
import type { CalendarEvent, EventPayload } from './types'

type ViewMode = 'day' | 'week' | 'month'

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export default function App() {
  const [view, setView] = useState<ViewMode>('month')
  const [selectedDay, setSelectedDay] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CalendarEvent | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [notifState, setNotifState] = useState<NotificationPermission | 'unsupported'>(
    'Notification' in window ? Notification.permission : 'unsupported',
  )
  const toastTimer = useRef<number | undefined>(undefined)

  const showToast = useCallback((msg: string) => {
    setToast(msg)
    window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(null), 2600)
  }, [])

  // Загружаем события с запасом ±2 месяца вокруг выбранного дня
  const loadEvents = useCallback(async () => {
    try {
      const start = subMonths(startOfMonth(selectedDay), 2)
      const end = addMonths(endOfMonth(selectedDay), 2)
      setEvents(await fetchEvents(start, end))
    } catch {
      showToast('Нет связи с сервером')
    }
  }, [selectedDay, showToast])

  useEffect(() => {
    loadEvents()
  }, [loadEvents])

  // Проверка напоминаний каждые 30 секунд
  useEffect(() => {
    const id = window.setInterval(() => checkReminders(events), 30_000)
    checkReminders(events)
    return () => window.clearInterval(id)
  }, [events])

  const dayEvents = useMemo(
    () =>
      events
        .filter((e) => isSameDay(new Date(e.start_time), selectedDay))
        .sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [events, selectedDay],
  )

  const upcoming = useMemo(() => {
    const now = new Date()
    return events
      .filter((e) => new Date(e.start_time) >= now)
      .sort((a, b) => a.start_time.localeCompare(b.start_time))
      .slice(0, 5)
  }, [events])

  function navigate(dir: 1 | -1) {
    if (view === 'month') setSelectedDay(dir === 1 ? addMonths(selectedDay, 1) : subMonths(selectedDay, 1))
    else if (view === 'week') setSelectedDay(dir === 1 ? addWeeks(selectedDay, 1) : subWeeks(selectedDay, 1))
    else setSelectedDay(addDays(selectedDay, dir))
  }

  async function handleSave(payload: EventPayload) {
    if (editing) {
      const updated = await updateEvent(editing.id, payload)
      setEvents((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
      showToast('Событие обновлено')
    } else {
      const created = await createEvent(payload)
      setEvents((prev) => [...prev, created])
      setSelectedDay(new Date(created.start_time))
      showToast('Событие добавлено')
    }
    setModalOpen(false)
    setEditing(null)
    if (payload.reminder_minutes != null) {
      const ok = await ensureNotificationPermission()
      setNotifState('Notification' in window ? Notification.permission : 'unsupported')
      if (!ok) showToast('Разрешите уведомления, чтобы получать напоминания')
    }
  }

  async function handleDelete() {
    if (!editing) return
    await deleteEvent(editing.id)
    setEvents((prev) => prev.filter((e) => e.id !== editing.id))
    setModalOpen(false)
    setEditing(null)
    showToast('Событие удалено')
  }

  async function enableNotifications() {
    const ok = await ensureNotificationPermission()
    setNotifState('Notification' in window ? Notification.permission : 'unsupported')
    showToast(ok ? 'Уведомления включены' : 'Уведомления заблокированы в браузере')
  }

  const headerDate =
    view === 'month'
      ? capitalize(format(selectedDay, 'LLLL yyyy', { locale: ru }))
      : capitalize(format(selectedDay, 'EEEE, d MMMM', { locale: ru }))

  const headerSub =
    view === 'week'
      ? `${format(startOfWeek(selectedDay, { weekStartsOn: 1 }), 'd MMM', { locale: ru })} — ${format(
          endOfWeek(selectedDay, { weekStartsOn: 1 }),
          'd MMM yyyy',
          { locale: ru },
        )}`
      : capitalize(format(new Date(), "'Сегодня' d MMMM", { locale: ru }))

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <div className="brand">
            <span className="brand-logo">⚖️</span>
            ZanProtect
          </div>
          <button className="today-btn" onClick={() => setSelectedDay(new Date())}>
            Сегодня
          </button>
        </div>
        <div className="header-date">{headerDate}</div>
        <div className="header-nav">
          <span className="header-sub">{headerSub}</span>
          <div className="nav-arrows">
            <button onClick={() => navigate(-1)} aria-label="Назад">‹</button>
            <button onClick={() => navigate(1)} aria-label="Вперёд">›</button>
          </div>
        </div>
        <div className="view-tabs">
          {(['day', 'week', 'month'] as ViewMode[]).map((v) => (
            <button key={v} className={view === v ? 'active' : ''} onClick={() => setView(v)}>
              {v === 'day' ? 'День' : v === 'week' ? 'Неделя' : 'Месяц'}
            </button>
          ))}
        </div>
      </header>

      <main className="content">
        {notifState === 'default' && (
          <div className="notif-banner">
            🔔 Включите уведомления, чтобы получать напоминания о заседаниях
            <button onClick={enableNotifications}>Включить</button>
          </div>
        )}

        {view === 'month' && (
          <>
            <MonthView
              month={selectedDay}
              selectedDay={selectedDay}
              events={events}
              onSelectDay={(d) => setSelectedDay(d)}
            />
            <section className="day-panel">
              <h3>{capitalize(format(selectedDay, 'EEEE, d MMMM', { locale: ru }))}</h3>
              {dayEvents.length === 0 ? (
                <div className="empty-state">
                  <span className="emoji">🗓️</span>
                  Нет событий — нажмите «+», чтобы добавить
                </div>
              ) : (
                dayEvents.map((e) => (
                  <EventCard
                    key={e.id}
                    event={e}
                    onClick={() => {
                      setEditing(e)
                      setModalOpen(true)
                    }}
                  />
                ))
              )}
            </section>
          </>
        )}

        {view === 'week' && (
          <>
            <WeekStrip
              anchor={selectedDay}
              selectedDay={selectedDay}
              events={events}
              onSelectDay={(d) => setSelectedDay(d)}
            />
            <section className="day-panel">
              <h3>{capitalize(format(selectedDay, 'EEEE, d MMMM', { locale: ru }))}</h3>
              {dayEvents.length === 0 ? (
                <div className="empty-state">
                  <span className="emoji">🗓️</span>
                  Нет событий в этот день
                </div>
              ) : (
                dayEvents.map((e) => (
                  <EventCard
                    key={e.id}
                    event={e}
                    onClick={() => {
                      setEditing(e)
                      setModalOpen(true)
                    }}
                  />
                ))
              )}
            </section>
          </>
        )}

        {view === 'day' && (
          <section className="day-panel">
            {dayEvents.length === 0 ? (
              <div className="empty-state">
                <span className="emoji">☀️</span>
                Свободный день — событий нет
              </div>
            ) : (
              dayEvents.map((e) => (
                <EventCard
                  key={e.id}
                  event={e}
                  onClick={() => {
                    setEditing(e)
                    setModalOpen(true)
                  }}
                />
              ))
            )}

            {upcoming.length > 0 && (
              <>
                <h3 style={{ marginTop: 24 }}>Ближайшие события</h3>
                {upcoming.map((e) => (
                  <EventCard
                    key={e.id}
                    event={e}
                    onClick={() => {
                      setEditing(e)
                      setModalOpen(true)
                    }}
                  />
                ))}
              </>
            )}
          </section>
        )}
      </main>

      <button
        className="fab"
        aria-label="Добавить событие"
        onClick={() => {
          setEditing(null)
          setModalOpen(true)
        }}
      >
        +
      </button>

      {modalOpen && (
        <EventModal
          initialDay={selectedDay}
          editing={editing}
          onSave={handleSave}
          onDelete={editing ? handleDelete : null}
          onClose={() => {
            setModalOpen(false)
            setEditing(null)
          }}
        />
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
