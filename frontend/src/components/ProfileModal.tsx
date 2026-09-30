import { useEffect, useState } from 'react'
import { setToken, updateCredentials } from '../api'
import type { User } from '../types'
import { IconClose } from './Icons'

interface Props {
  user: User
  onUpdated: (user: User) => void
  onClose: () => void
}

/** Каждый сотрудник сам меняет имя, логин и пароль — вход дальше по новым данным. */
export default function ProfileModal({ user, onUpdated, onClose }: Props) {
  const [name, setName] = useState(user.name)
  const [loginName, setLoginName] = useState(user.login)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setDone(false)

    const nextName = name.trim()
    const nextLogin = loginName.trim().toLowerCase()

    if (!currentPassword) {
      setError('Введите текущий пароль — без него изменить данные нельзя')
      return
    }
    if (!nextName) {
      setError('Имя не может быть пустым')
      return
    }
    if (nextLogin.length < 3) {
      setError('Логин должен быть не короче 3 символов')
      return
    }
    if (newPassword && newPassword.length < 6) {
      setError('Новый пароль должен быть не короче 6 символов')
      return
    }
    if (newPassword && newPassword !== repeatPassword) {
      setError('Новый пароль и повтор не совпадают')
      return
    }

    const payload: { current_password: string; login?: string; name?: string; password?: string } = {
      current_password: currentPassword,
    }
    if (nextLogin !== user.login) payload.login = nextLogin
    if (nextName !== user.name) payload.name = nextName
    if (newPassword) payload.password = newPassword

    if (payload.login === undefined && payload.name === undefined && payload.password === undefined) {
      setError('Изменений нет')
      return
    }

    setBusy(true)
    try {
      const { token, user: updated } = await updateCredentials(payload)
      setToken(token)
      onUpdated(updated)
      setCurrentPassword('')
      setNewPassword('')
      setRepeatPassword('')
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-head">
          <h2>Мой аккаунт</h2>
          <button className="modal-close" onClick={onClose} aria-label="Закрыть">
            <IconClose size={14} />
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}
        {done && <div className="form-ok">Данные сохранены. В следующий раз входите по новым логину и паролю.</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Имя</label>
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={200} />
          </div>

          <div className="field">
            <label>Логин</label>
            <input
              value={loginName}
              onChange={(e) => setLoginName(e.target.value)}
              maxLength={100}
              autoCapitalize="none"
              autoComplete="username"
            />
            <div className="field-hint">Логин приводится к нижнему регистру.</div>
          </div>

          <div className="field">
            <label>Текущий пароль</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              maxLength={200}
              autoComplete="current-password"
            />
          </div>

          <div className="field-row">
            <div className="field">
              <label>Новый пароль</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                maxLength={200}
                autoComplete="new-password"
                placeholder="Мин. 6 символов"
              />
            </div>
            <div className="field">
              <label>Повторите пароль</label>
              <input
                type="password"
                value={repeatPassword}
                onChange={(e) => setRepeatPassword(e.target.value)}
                maxLength={200}
                autoComplete="new-password"
              />
            </div>
          </div>
          <div className="field-hint">Оставьте поля пароля пустыми, если меняете только имя или логин.</div>

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
              Закрыть
            </button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? 'Сохранение…' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
