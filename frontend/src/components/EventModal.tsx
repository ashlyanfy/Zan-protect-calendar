import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import type { CalendarEvent, EventPayload, EventType } from '../types'
import { EVENT_TYPE_META, REMINDER_OPTIONS } from '../types'

interface Props {
  initialDay: Date
  editing: CalendarEvent | null
  canEdit: boolean
  onSave: (payload: EventPayload) => Promise<void>
  onDelete: (() => Promise<void>) | null
  onClose: () => void
}

export default function EventModal({ initialDay, editing, canEdit, onSave, onDelete, onClose }: Props) {
  const [title, setTitle] = useState(editing?.title ?? '')
  const [eventType, setEventType] = useState<EventType>(editing?.event_type ?? 'court')
  const [date, setDate] = useState(
    format(editing ? new Date(editing.start_time) : initialDay, 'yyyy-MM-dd'),
  )
  const [startTime, setStartTime] = useState(
    editing ? format(new Date(editing.start_time), 'HH:mm') : '10:00',
  )
  const [endTime, setEndTime] = useState(
    editing?.end_time ? format(new Date(editing.end_time), 'HH:mm') : '',
  )
  const [location, setLocation] = useState(editing?.location ?? '')
  const [caseNumber, setCaseNumber] = useState(editing?.case_number ?? '')
  const [description, setDescription] = useState(editing?.description ?? '')
  const [reminder, setReminder] = useState<string>(
    editing?.reminder_minutes != null ? String(editing.reminder_minutes) : '',
  )
  const [isShared, setIsShared] = useState(editing?.is_shared ?? false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSave() {
    setError(null)
    if (!title.trim()) {
      setError('Укажите название события')
      return
    }
    if (!date || !startTime) {
      setError('Укажите дату и время начала')
      return
    }
    const start = new Date(`${date}T${startTime}`)
    const end = endTime ? new Date(`${date}T${endTime}`) : null
    if (end && end <= start) {
      setError('Время окончания должно быть позже начала')
      return
    }
    setBusy(true)
    try {
      await onSave({
        title: title.trim(),
        description: description.trim() || null,
        event_type: eventType,
        location: location.trim() || null,
        case_number: caseNumber.trim() || null,
        start_time: start.toISOString(),
        end_time: end ? end.toISOString() : null,
        reminder_minutes: reminder === '' ? null : Number(reminder),
        is_shared: isShared,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось сохранить')
      setBusy(false)
    }
  }

  async function handleDelete() {
    if (!onDelete) return
    if (!window.confirm('Удалить это событие?')) return
    setBusy(true)
    try {
      await onDelete()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось удалить')
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-handle" />
        <h2>{!canEdit ? 'Просмотр события' : editing ? 'Редактировать событие' : 'Новое событие'}</h2>

        {!canEdit && editing?.owner_name && (
          <div className="notif-banner" style={{ marginBottom: 14 }}>
            👥 Общее событие, автор — {editing.owner_name}
          </div>
        )}
        {error && <div className="form-error">{error}</div>}

        <fieldset disabled={!canEdit} style={{ border: 'none' }}>
        <div className="field">
          <label>Название *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Судебное заседание по делу…"
            maxLength={200}
            autoFocus={!editing}
          />
        </div>

        <div className="field">
          <label>Тип события</label>
          <div className="type-chips">
            {(Object.keys(EVENT_TYPE_META) as EventType[]).map((t) => {
              const meta = EVENT_TYPE_META[t]
              const active = eventType === t
              return (
                <button
                  key={t}
                  type="button"
                  className="type-chip"
                  style={
                    active
                      ? { background: meta.bg, color: meta.color, borderColor: meta.color }
                      : undefined
                  }
                  onClick={() => setEventType(t)}
                >
                  {meta.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="field">
          <label>Дата *</label>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>

        <div className="field-row">
          <div className="field">
            <label>Начало *</label>
            <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </div>
          <div className="field">
            <label>Окончание</label>
            <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label>Видимость</label>
          <div className="type-chips">
            <button
              type="button"
              className="type-chip"
              style={!isShared ? { background: '#e7eefc', color: '#2f6bd8', borderColor: '#2f6bd8' } : undefined}
              onClick={() => setIsShared(false)}
            >
              🔒 Личное
            </button>
            <button
              type="button"
              className="type-chip"
              style={isShared ? { background: '#e3f4f1', color: '#22867a', borderColor: '#22867a' } : undefined}
              onClick={() => setIsShared(true)}
            >
              👥 Общее для всех
            </button>
          </div>
        </div>

        <div className="field">
          <label>Напоминание 🔔</label>
          <select value={reminder} onChange={(e) => setReminder(e.target.value)}>
            {REMINDER_OPTIONS.map((o) => (
              <option key={o.label} value={o.value == null ? '' : o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Место</label>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Суд, адрес, кабинет…"
            maxLength={300}
          />
        </div>

        <div className="field">
          <label>Номер дела</label>
          <input
            value={caseNumber}
            onChange={(e) => setCaseNumber(e.target.value)}
            placeholder="№ 2-1234/2026"
            maxLength={100}
          />
        </div>

        <div className="field">
          <label>Заметки</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Детали, документы, участники…"
            maxLength={5000}
          />
        </div>
        </fieldset>

        <div className="modal-actions">
          {canEdit && onDelete && (
            <button className="btn btn-danger" onClick={handleDelete} disabled={busy}>
              🗑
            </button>
          )}
          <button className="btn btn-ghost" onClick={onClose} disabled={busy}>
            {canEdit ? 'Отмена' : 'Закрыть'}
          </button>
          {canEdit && (
            <button className="btn btn-primary" onClick={handleSave} disabled={busy}>
              {busy ? 'Сохранение…' : 'Сохранить'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
