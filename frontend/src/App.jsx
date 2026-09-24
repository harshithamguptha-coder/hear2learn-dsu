import { Link, Route, Routes } from 'react-router-dom'

import StudentPage from './pages/StudentPage'
import TeacherPage from './pages/TeacherPage'

function HomePage() {
  return (
    <main className="shell home-shell">
      <section className="hero" aria-labelledby="home-title">
        <p className="eyebrow">Live learning, made more accessible</p>
        <h1 id="home-title">Accessible Classroom</h1>
        <p className="hero-copy">
          Start a lecture, speak naturally, and share a live transcript with
          every student who joins.
        </p>
        <div className="role-grid">
          <Link className="role-card" to="/teacher">
            <span className="role-icon" aria-hidden="true">T</span>
            <span>
              <strong>Teacher</strong>
              <small>Start a lecture and speak</small>
            </span>
          </Link>
          <Link className="role-card" to="/student">
            <span className="role-icon" aria-hidden="true">S</span>
            <span>
              <strong>Student</strong>
              <small>Join with a session ID</small>
            </span>
          </Link>
        </div>
      </section>
    </main>
  )
}

export default function App() {
  return (
    <div className="app-frame">
      <header className="site-header">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span>Accessible Classroom</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link to="/teacher">Teacher</Link>
          <Link to="/student">Student</Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/teacher" element={<TeacherPage />} />
        <Route path="/student" element={<StudentPage />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </div>
  )
}
