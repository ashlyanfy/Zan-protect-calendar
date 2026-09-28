import { useState } from 'react'
import { login, setToken } from '../api'
import type { User } from '../types'

export default function LoginScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!loginName.trim() || !password) {
      setError('Введите логин и пароль')
      return
    }
    setBusy(true)
    try {
      const { token, user } = await login(loginName.trim(), password)
      setToken(token)
      onLogin(user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти')
      setBusy(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-hero">
        <img src="/logo.webp" alt="ZanProtect" className="login-logo" />
        <p>Календарь юридических событий</p>
      </div>
      <form className="login-card" onSubmit={handleSubmit}>
        <h2>Вход</h2>
        {error && <div className="form-error">{error}</div>}
        <div className="field">
          <label>Логин</label>
          <input
            value={loginName}
            onChange={(e) => setLoginName(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            autoFocus
          />
        </div>
        <div className="field">
          <label>Пароль</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </div>
  )
}
