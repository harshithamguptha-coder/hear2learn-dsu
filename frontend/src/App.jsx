import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { AuthProvider, useAuth } from './context/AuthContext'
import { LectureProvider } from './context/LectureContext'
import LoginPage from './pages/LoginPage'
import ProtectedRoute, { PublicOnlyRoute } from './components/ProtectedRoute'
import RegisterPage from './pages/RegisterPage'
import StudentPage from './pages/StudentPage'
import TeacherPage from './pages/TeacherPage'

function HomePage() {
  const { user } = useAuth()
  const destination = user?.role === 'teacher' ? '/teacher' : '/student'
  return (
    <main className="shell home-shell">
      <section className="hero" aria-labelledby="home-title">
        <p className="eyebrow">Live learning, made more accessible</p>
        <h1 id="home-title">Accessible Classroom</h1>
        <p className="hero-copy">
          {user ? `Welcome back, ${user.name}. Continue your live classroom.` : 'Create an account to start or join a live accessible classroom.'}
        </p>
        <div className="role-grid">
          <Link className="role-card" to={user ? destination : '/register?role=teacher'}>
            <span className="role-icon" aria-hidden="true">T</span>
            <span>
              <strong>Teacher</strong>
              <small>Start a lecture and speak</small>
            </span>
          </Link>
          <Link className="role-card" to={user ? destination : '/register?role=student'}>
            <span className="role-icon" aria-hidden="true">S</span>
            <span>
              <strong>Student</strong>
              <small>Join with a session ID</small>
            </span>
          </Link>
        </div>
        {!user && (
          <p className="home-account-links">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        )}
      </section>
    </main>
  )
}

function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/', { replace: true })
  }

  if (user) return null

  return (
    <header className="site-header">
      <Link className="brand" to="/">
        <span className="brand-mark" aria-hidden="true">A</span>
        <span>Accessible Classroom</span>
      </Link>
      <nav aria-label="Main navigation">
        {user ? (
          <>
            <span className="account-chip">{user.name} · {user.role}</span>
            <Link to={user.role === 'teacher' ? '/teacher' : '/student'}>Dashboard</Link>
            <button className="nav-button" type="button" onClick={handleLogout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
    </header>
  )
}

function AppRoutes() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
        <Route path="/register" element={<PublicOnlyRoute><RegisterPage /></PublicOnlyRoute>} />
        <Route path="/teacher" element={<ProtectedRoute role="teacher"><TeacherPage /></ProtectedRoute>} />
        <Route path="/student" element={<ProtectedRoute role="student"><StudentPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <LectureProvider>
        <div className="app-frame">
          <AppRoutes />
        </div>
      </LectureProvider>
    </AuthProvider>
  )
}
