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
import {
  UnauthorizedError,
  createEvent,
  deleteEvent,
  fetchEvents,
  fetchMe,
  getToken,
  setToken,
  updateEvent,
} from './api'
import MonthView from './components/MonthView'
import WeekStrip from './components/WeekStrip'
import EventCard from './components/EventCard'
import EventModal from './components/EventModal'
import LoginScreen from './components/LoginScreen'
import TeamModal from './components/TeamModal'
import ProfileModal from './components/ProfileModal'
import {
  IconArrowLeft,
  IconBell,
  IconChevronLeft,
  IconChevronRight,
  IconLogout,
  IconPlus,
  IconSettings,
  IconUsers,
} from './components/Icons'
import { checkReminders, ensureNotificationPermission } from './notifications'
import type { CalendarEvent, EventPayload, User } from './types'

type ViewMode = 'day' | 'week' | 'month'

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [view, setView] = useState<ViewMode>('month')
  const [selectedDay, setSelectedDay] = useState(new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CalendarEvent | null>(null)
  const [teamOpen, setTeamOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  // Админ смотрит календарь сотрудника
  const [viewingUser, setViewingUser] = useState<User | null>(null)
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

  // Восстанавливаем сессию по сохранённому токену
  useEffect(() => {
    if (!getToken()) {
      setAuthChecked(true)
      return
    }
    fetchMe()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setAuthChecked(true))
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setEvents([])
    setViewingUser(null)
  }, [])

  const targetUserId = viewingUser ? viewingUser.id : null

  // Загружаем события с запасом ±2 месяца вокруг выбранного дня
  const loadEvents = useCallback(async () => {
    if (!user) return
    try {
      const start = subMonths(startOfMonth(selectedDay), 2)
      const end = addMonths(endOfMonth(selectedDay), 2)
      setEvents(await fetchEvents(start, end, targetUserId))
    } catch (e) {
      if (e instanceof UnauthorizedError) logout()
      else showToast('Нет связи с сервером')
    }
  }, [selectedDay, user, targetUserId, logout, showToast])

  useEffect(() => {
    loadEvents()
  }, [loadEvents])

  // Напоминания — только для собственного календаря
  useEffect(() => {
    if (viewingUser) return
    const id = window.setInterval(() => checkReminders(events), 30_000)
    checkReminders(events)
    return () => window.clearInterval(id)
  }, [events, viewingUser])

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
    try {
      await doSave(payload)
    } catch (e) {
      if (e instanceof UnauthorizedError) {
        logout()
        return
      }
      throw e
    }
  }

  async function doSave(payload: EventPayload) {
    if (editing) {
      const updated = await updateEvent(editing.id, payload)
      setEvents((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
      showToast('Событие обновлено')
    } else {
      const created = await createEvent(payload, targetUserId)
      setEvents((prev) => [...prev, created])
      setSelectedDay(new Date(created.start_time))
      showToast('Событие добавлено')
    }
    setModalOpen(false)
    setEditing(null)
    if (payload.reminder_minutes != null && !viewingUser) {
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
      : capitalize(format(new Date(), "'сегодня' d MMMM yyyy", { locale: ru }))

  if (!authChecked) return null
  if (!user) return <LoginScreen onLogin={setUser} />

  const canEditSelected = editing == null || user.role === 'admin' || editing.owner_id === user.id

  function openEvent(e: CalendarEvent) {
    setEditing(e)
    setModalOpen(true)
  }

  const dayTitle = capitalize(format(selectedDay, 'EEEE, d MMMM', { locale: ru }))

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <img src="/logo.webp" alt="ZanProtect" className="brand-img" />
          <div className="header-actions">
            <span className="user-name">{user.name}</span>
            {user.role === 'admin' && (
              <button className="icon-btn" onClick={() => setTeamOpen(true)} aria-label="Сотрудники" title="Сотрудники">
                <IconUsers size={16} />
              </button>
            )}
            <button
              className="icon-btn"
              onClick={() => setProfileOpen(true)}
              aria-label="Мой аккаунт"
              title="Мой аккаунт"
            >
              <IconSettings size={16} />
            </button>
            <button className="today-btn" onClick={() => setSelectedDay(new Date())}>
              Сегодня
            </button>
            <button className="icon-btn" onClick={logout} aria-label="Выйти" title="Выйти">
              <IconLogout size={16} />
            </button>
          </div>
        </div>

        <div className="header-nav">
          <div>
            <div className="header-date">{headerDate}</div>
            <span className="header-sub">{headerSub}</span>
          </div>
          <div className="nav-arrows">
            <button onClick={() => navigate(-1)} aria-label="Назад">
              <IconChevronLeft size={16} />
            </button>
            <button onClick={() => navigate(1)} aria-label="Вперёд">
              <IconChevronRight size={16} />
            </button>
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

      {viewingUser && (
        <div className="viewing-bar">
          <span className="vb-label">Календарь сотрудника</span>
          <span className="vb-name">
            {viewingUser.name} · {viewingUser.login}
          </span>
          <button onClick={() => setViewingUser(null)}>
            <IconArrowLeft size={14} />
            Мой календарь
          </button>
        </div>
      )}

      <main className="content">
        {notifState === 'default' && !viewingUser && (
          <div className="notif-banner">
            <IconBell size={16} />
            Включите уведомления, чтобы получать напоминания о заседаниях
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
              <h3>{dayTitle}</h3>
              {dayEvents.length === 0 ? (
                <div className="empty-state">Событий нет</div>
              ) : (
                dayEvents.map((e) => <EventCard key={e.id} event={e} onClick={() => openEvent(e)} />)
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
              <h3>{dayTitle}</h3>
              {dayEvents.length === 0 ? (
                <div className="empty-state">Событий нет</div>
              ) : (
                dayEvents.map((e) => <EventCard key={e.id} event={e} onClick={() => openEvent(e)} />)
              )}
            </section>
          </>
        )}

        {view === 'day' && (
          <section className="day-panel">
            <h3>{dayTitle}</h3>
            {dayEvents.length === 0 ? (
              <div className="empty-state">Событий нет</div>
            ) : (
              dayEvents.map((e) => <EventCard key={e.id} event={e} onClick={() => openEvent(e)} />)
            )}

            {upcoming.length > 0 && (
              <section className="day-panel">
                <h3>Ближайшие события</h3>
                {upcoming.map((e) => (
                  <EventCard key={e.id} event={e} onClick={() => openEvent(e)} />
                ))}
              </section>
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
        <IconPlus size={16} />
        Событие
      </button>

      {modalOpen && (
        <EventModal
          initialDay={selectedDay}
          editing={editing}
          canEdit={canEditSelected}
          ownerLabel={viewingUser ? viewingUser.name : null}
          onSave={handleSave}
          onDelete={editing ? handleDelete : null}
          onClose={() => {
            setModalOpen(false)
            setEditing(null)
          }}
        />
      )}

      {teamOpen && (
        <TeamModal
          currentUser={user}
          onOpenCalendar={(u) => {
            setViewingUser(u)
            setTeamOpen(false)
            setSelectedDay(new Date())
          }}
          onClose={() => setTeamOpen(false)}
        />
      )}

      {profileOpen && (
        <ProfileModal
          user={user}
          onUpdated={(u) => {
            setUser(u)
            showToast('Данные аккаунта обновлены')
          }}
          onClose={() => setProfileOpen(false)}
        />
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
