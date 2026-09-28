import { useEffect, useState } from 'react'
import { createUser, deleteUser, fetchUsers } from '../api'
import type { User } from '../types'

export default function TeamModal({ onClose }: { onClose: () => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch((e) => setError(e instanceof Error ? e.message : 'Не удалось загрузить список'))
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim() || !loginName.trim() || password.length < 6) {
      setError('Заполните имя, логин и пароль (минимум 6 символов)')
      return
    }
    setBusy(true)
    try {
      const user = await createUser({ name: name.trim(), login: loginName.trim(), password })
      setUsers((prev) => [...prev, user])
      setName('')
      setLoginName('')
      setPassword('')
      setShowForm(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать аккаунт')
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(user: User) {
    if (!window.confirm(`Удалить аккаунт «${user.name}» и все его события?`)) return
    setError(null)
    try {
      await deleteUser(user.id)
      setUsers((prev) => prev.filter((u) => u.id !== user.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить')
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-handle" />
        <h2>Сотрудники</h2>
        {error && <div className="form-error">{error}</div>}

        <div className="team-list">
          {users.map((u) => (
            <div key={u.id} className="team-row">
              <div className="team-avatar">{u.name.charAt(0).toUpperCase()}</div>
              <div className="team-info">
                <span className="team-name">
                  {u.name}
                  {u.role === 'admin' && <span className="team-role">админ</span>}
                </span>
                <span className="team-login">@{u.login}</span>
              </div>
              {u.role !== 'admin' && (
                <button className="team-delete" onClick={() => handleDelete(u)} aria-label="Удалить">
                  🗑
                </button>
              )}
            </div>
          ))}
        </div>

        {showForm ? (
          <form onSubmit={handleCreate}>
            <div className="field">
              <label>Имя сотрудника *</label>
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={200} autoFocus />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Логин *</label>
                <input
                  value={loginName}
                  onChange={(e) => setLoginName(e.target.value)}
                  maxLength={100}
                  autoCapitalize="none"
                  autoComplete="off"
                />
              </div>
              <div className="field">
                <label>Пароль * (мин. 6)</label>
                <input
                  type="text"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  maxLength={200}
                  autoComplete="new-password"
                />
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)} disabled={busy}>
                Отмена
              </button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Создание…' : 'Создать аккаунт'}
              </button>
            </div>
          </form>
        ) : (
          <div className="modal-actions">
            <button className="btn btn-ghost" onClick={onClose}>
              Закрыть
            </button>
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>
              + Новый сотрудник
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
