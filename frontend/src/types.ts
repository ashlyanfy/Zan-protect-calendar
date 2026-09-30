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
  court: { label: 'Суд', color: '#8e2b36', bg: '#f6ecec' },
  meeting: { label: 'Встреча', color: '#1f4c86', bg: '#eaeff6' },
  deadline: { label: 'Дедлайн', color: '#8a5512', bg: '#f7f1e7' },
  consultation: { label: 'Консультация', color: '#1d6355', bg: '#e9f1ef' },
  other: { label: 'Другое', color: '#4e5866', bg: '#eef0f3' },
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
