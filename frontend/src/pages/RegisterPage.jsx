import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedRole = searchParams.get('role') === 'student' ? 'student' : 'teacher'
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: requestedRole,
  })
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
      const registeredUser = await register(form)
      navigate(registeredUser.role === 'teacher' ? '/teacher' : '/student', { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="shell auth-shell">
      <section className="auth-card" aria-labelledby="register-title">
        <p className="eyebrow">Get started</p>
        <h1 id="register-title">Create your account</h1>
        <p className="auth-intro">Choose a role now. Your account and lectures stay in the database.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="register-name">Full name</label>
          <input
            id="register-name"
            name="name"
            value={form.name}
            onChange={updateField}
            autoComplete="name"
            minLength={2}
            maxLength={100}
            required
          />
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            name="email"
            type="email"
            value={form.email}
            onChange={updateField}
            autoComplete="email"
            required
          />
          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            name="password"
            type="password"
            value={form.password}
            onChange={updateField}
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            required
          />
          <label htmlFor="register-role">I am a</label>
          <select id="register-role" name="role" value={form.role} onChange={updateField}>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </select>
          {error && <p className="message error" role="alert">{error}</p>}
          <button className="primary-button auth-submit" type="submit" disabled={busy}>
            {busy ? 'Creating account…' : 'Register'}
          </button>
        </form>
        <p className="auth-switch">Already registered? <Link to="/login">Log in</Link></p>
      </section>
    </main>
  )
}
