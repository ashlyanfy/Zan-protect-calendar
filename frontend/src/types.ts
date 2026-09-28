export type EventType = 'court' | 'meeting' | 'deadline' | 'consultation' | 'other'

export interface CalendarEvent {
  id: string
  title: string
  description: string | null
  event_type: EventType
  location: string | null
  case_number: string | null
  start_time: string
  end_time: string | null
  reminder_minutes: number | null
  is_shared: boolean
  owner_id: string | null
  owner_name: string | null
  created_at: string
  updated_at: string
}

export interface EventPayload {
  title: string
  description: string | null
  event_type: EventType
  location: string | null
  case_number: string | null
  start_time: string
  end_time: string | null
  reminder_minutes: number | null
  is_shared: boolean
}

export interface User {
  id: string
  login: string
  name: string
  role: 'admin' | 'employee'
  created_at: string
}

export const EVENT_TYPE_META: Record<EventType, { label: string; color: string; bg: string }> = {
  court: { label: 'Суд', color: '#b03a48', bg: '#fbe9eb' },
  meeting: { label: 'Встреча', color: '#2f6bd8', bg: '#e7eefc' },
  deadline: { label: 'Дедлайн', color: '#b06a1f', bg: '#fdf0df' },
  consultation: { label: 'Консультация', color: '#22867a', bg: '#e3f4f1' },
  other: { label: 'Другое', color: '#5b6478', bg: '#eceff5' },
}

export const REMINDER_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: 'Без напоминания' },
  { value: 5, label: 'За 5 минут' },
  { value: 15, label: 'За 15 минут' },
  { value: 30, label: 'За 30 минут' },
  { value: 60, label: 'За 1 час' },
  { value: 120, label: 'За 2 часа' },
  { value: 1440, label: 'За 1 день' },
  { value: 2880, label: 'За 2 дня' },
]
