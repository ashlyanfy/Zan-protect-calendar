import { useEffect, useState } from 'react'
import { createUser, deleteUser, fetchUsers, updateUser } from '../api'
import type { User } from '../types'
import { IconCalendar, IconClose, IconKey, IconTrash } from './Icons'

interface Props {
  currentUser: User
  onOpenCalendar: (user: User) => void
  onClose: () => void
}

/** Панель администратора: аккаунты сотрудников, их доступы и календари. */
export default function TeamModal({ currentUser, onOpenCalendar, onClose }: Props) {
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editLogin, setEditLogin] = useState('')
  const [editPassword, setEditPassword] = useState('')

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

  function startEdit(user: User) {
    setError(null)
    setNotice(null)
    setShowForm(false)
    setEditingId(user.id)
    setEditName(user.name)
    setEditLogin(user.login)
    setEditPassword('')
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setNotice(null)
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
      setNotice(`Аккаунт «${user.name}» создан`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать аккаунт')
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!editingId) return
    setError(null)
    setNotice(null)

    const target = users.find((u) => u.id === editingId)
    if (!target) return

    const nextName = editName.trim()
    const nextLogin = editLogin.trim().toLowerCase()
    if (!nextName) {
      setError('Имя не может быть пустым')
      return
    }
    if (nextLogin.length < 3) {
      setError('Логин должен быть не короче 3 символов')
      return
    }
    if (editPassword && editPassword.length < 6) {
      setError('Пароль должен быть не короче 6 символов')
      return
    }

    const payload: { login?: string; name?: string; password?: string } = {}
    if (nextLogin !== target.login) payload.login = nextLogin
    if (nextName !== target.name) payload.name = nextName
    if (editPassword) payload.password = editPassword
    if (Object.keys(payload).length === 0) {
      setEditingId(null)
      return
    }

    setBusy(true)
    try {
      const updated = await updateUser(editingId, payload)
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      setEditingId(null)
      setNotice(`Данные «${updated.name}» обновлены`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить')
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(user: User) {
    if (!window.confirm(`Удалить аккаунт «${user.name}» и все его события?`)) return
    setError(null)
    setNotice(null)
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
        <div className="modal-head">
          <h2>Сотрудники</h2>
          <button className="modal-close" onClick={onClose} aria-label="Закрыть">
            <IconClose size={14} />
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}
        {notice && <div className="form-ok">{notice}</div>}

        <div className="team-list">
          {users.map((u) => (
            <div key={u.id}>
              <div className="team-row">
                <div className="team-avatar">{u.name.charAt(0).toUpperCase()}</div>
                <div className="team-info">
                  <span className="team-name">
                    {u.name}
                    {u.role === 'admin' && <span className="team-role">админ</span>}
                  </span>
                  <span className="team-login">{u.login}</span>
                </div>
                <div className="team-actions">
                  {u.id !== currentUser.id && (
                    <button
                      className="team-btn"
                      onClick={() => onOpenCalendar(u)}
                      title="Открыть календарь сотрудника"
                      aria-label="Открыть календарь сотрудника"
                    >
                      <IconCalendar size={15} />
                    </button>
                  )}
                  <button
                    className="team-btn"
                    onClick={() => startEdit(u)}
                    title="Логин и пароль"
                    aria-label="Изменить логин и пароль"
                  >
                    <IconKey size={15} />
                  </button>
                  {u.role !== 'admin' && (
                    <button
                      className="team-btn danger"
                      onClick={() => handleDelete(u)}
                      title="Удалить аккаунт"
                      aria-label="Удалить аккаунт"
                    >
                      <IconTrash size={15} />
                    </button>
                  )}
                </div>
              </div>

              {editingId === u.id && (
                <form className="team-edit" onSubmit={handleSaveEdit}>
                  <div className="section-title">Доступ сотрудника</div>
                  <div className="field">
                    <label>Имя</label>
                    <input value={editName} onChange={(e) => setEditName(e.target.value)} maxLength={200} autoFocus />
                  </div>
                  <div className="field-row">
                    <div className="field">
                      <label>Логин</label>
                      <input
                        value={editLogin}
                        onChange={(e) => setEditLogin(e.target.value)}
                        maxLength={100}
                        autoCapitalize="none"
                        autoComplete="off"
                      />
                    </div>
                    <div className="field">
                      <label>Новый пароль</label>
                      <input
                        type="text"
                        value={editPassword}
                        onChange={(e) => setEditPassword(e.target.value)}
                        maxLength={200}
                        autoComplete="off"
                        placeholder="Оставьте пустым"
                      />
                    </div>
                  </div>
                  <div className="modal-actions">
                    <button type="button" className="btn btn-ghost" onClick={() => setEditingId(null)} disabled={busy}>
                      Отмена
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={busy}>
                      {busy ? 'Сохранение…' : 'Сохранить'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          ))}
        </div>

        {showForm ? (
          <form onSubmit={handleCreate} style={{ marginTop: 22 }}>
            <div className="section-title">Новый сотрудник</div>
            <div className="field">
              <label>Имя сотрудника</label>
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={200} autoFocus />
            </div>
            <div className="field-row">
              <div className="field">
                <label>Логин</label>
                <input
                  value={loginName}
                  onChange={(e) => setLoginName(e.target.value)}
                  maxLength={100}
                  autoCapitalize="none"
                  autoComplete="off"
                />
              </div>
              <div className="field">
                <label>Пароль (мин. 6)</label>
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
              Новый сотрудник
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
