import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const loggedInUser = await login(form)
      const requestedPath = location.state?.from
      const allowedPath =
        requestedPath === (loggedInUser.role === 'teacher' ? '/teacher' : '/student')
          ? requestedPath
          : loggedInUser.role === 'teacher'
            ? '/teacher'
            : '/student'
      navigate(allowedPath, { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="shell auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <p className="eyebrow">Welcome back</p>
        <h1 id="login-title">Log in</h1>
        <p className="auth-intro">Continue to your Teacher or Student dashboard.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            name="email"
            type="email"
            value={form.email}
            onChange={updateField}
            autoComplete="email"
            required
          />
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            name="password"
            type="password"
            value={form.password}
            onChange={updateField}
            autoComplete="current-password"
            required
          />
          {error && <p className="message error" role="alert">{error}</p>}
          <button className="primary-button auth-submit" type="submit" disabled={busy}>
            {busy ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        <p className="auth-switch">New here? <Link to="/register">Create an account</Link></p>
      </section>
    </main>
  )
}
