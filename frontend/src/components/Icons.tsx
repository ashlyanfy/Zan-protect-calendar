/** Минимальные линейные иконки — вместо эмодзи. Наследуют цвет текста. */
interface IconProps {
  size?: number
  className?: string
}

function Svg({ size = 16, className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function IconUsers(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M2 20v-1.5c0-2.2 2.5-3.5 5.5-3.5s5.5 1.3 5.5 3.5V20" />
      <circle cx="7.5" cy="8.5" r="3.2" />
      <path d="M15.5 15.4c2.7.3 4.5 1.5 4.5 3.1V20" />
      <path d="M15.2 5.6a3.2 3.2 0 0 1 0 6" />
    </Svg>
  )
}

export function IconLogout(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M14 4H5v16h9" />
      <path d="M18 12H9" />
      <path d="m15 8 4 4-4 4" />
    </Svg>
  )
}

export function IconSettings(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
      <path d="M16 4v6M8 14v6" />
    </Svg>
  )
}

export function IconPlus(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M12 5v14M5 12h14" />
    </Svg>
  )
}

export function IconChevronLeft(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="m14 5-7 7 7 7" />
    </Svg>
  )
}

export function IconChevronRight(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="m10 5 7 7-7 7" />
    </Svg>
  )
}

export function IconTrash(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M4 6h16" />
      <path d="M7 6V3h10v3" />
      <path d="M6 6v15h12V6" />
      <path d="M10 10v7M14 10v7" />
    </Svg>
  )
}

export function IconBell(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M6 9a6 6 0 0 1 12 0v5l2 3H4l2-3V9Z" />
      <path d="M10 20h4" />
    </Svg>
  )
}

export function IconPin(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M12 21s6.5-7 6.5-11.5a6.5 6.5 0 1 0-13 0C5.5 14 12 21 12 21Z" />
      <circle cx="12" cy="9.5" r="2.4" />
    </Svg>
  )
}

export function IconLock(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="5" y="10" width="14" height="11" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </Svg>
  )
}

export function IconCalendar(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="3.5" y="5" width="17" height="16" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </Svg>
  )
}

export function IconKey(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="8" cy="12" r="4" />
      <path d="M12 12h9M17 12v4M20 12v3" />
    </Svg>
  )
}

export function IconArrowLeft(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M20 12H4" />
      <path d="m10 6-6 6 6 6" />
    </Svg>
  )
}

export function IconClose(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Svg>
  )
}
