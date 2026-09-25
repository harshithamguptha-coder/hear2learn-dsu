import { useEffect, useState } from 'react'

import { getTeacherDashboard } from '../api/client'

const ACCESSIBILITY_MODES = [
  ['standard', 'Standard'],
  ['simplified', 'Simplified'],
  ['translation', 'Translation'],
  ['sign_support', 'Sign Support'],
]

function formatDate(value) {
  if (!value) return 'No data'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function formatTime(value) {
  if (!value) return 'No data'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function formatDuration(seconds) {
  const totalMinutes = Math.max(0, Math.floor(Number(seconds || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function TeacherDashboard({ token, refreshKey = 0 }) {
  const [dashboard, setDashboard] = useState({ total_lectures: 0, lectures: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [manualRefresh, setManualRefresh] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getTeacherDashboard(token)
      .then((data) => {
        if (!cancelled) setDashboard(data)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setDashboard({ total_lectures: 0, lectures: [] })
          setError(`Dashboard data is unavailable: ${requestError.message}`)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [token, refreshKey, manualRefresh])

  return (
    <section className="teacher-dashboard" aria-labelledby="teacher-dashboard-title">
      <div className="teacher-dashboard-header">
        <div>
          <p className="notes-kicker">Classroom overview</p>
          <h2 id="teacher-dashboard-title">Lecture Analytics</h2>
          <p>Stored attendance, questions, detected topics, and saved accessibility modes.</p>
        </div>
        <div className="teacher-dashboard-summary">
          <strong>{dashboard.total_lectures}</strong>
          <span>Total lectures</span>
        </div>
        <button
          className="teacher-dashboard-refresh"
          type="button"
          onClick={() => setManualRefresh((value) => value + 1)}
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && <p className="message error" role="alert">{error}</p>}
      {loading && dashboard.lectures.length === 0 && (
        <p className="history-message" role="status">Loading your lecture records…</p>
      )}
      {!loading && !error && dashboard.lectures.length === 0 && (
        <p className="history-message">Lectures you create will appear here with real stored data.</p>
      )}

      {dashboard.lectures.length > 0 && (
        <div className="teacher-recent-lectures">
          <h3>Recent lectures <span>Newest first</span></h3>
          <div className="teacher-lecture-list">
          {dashboard.lectures.map((lecture) => (
            <article className="teacher-lecture-card" key={lecture.session_id}>
              <header className="teacher-lecture-card-header">
                <div>
                  <h3>{lecture.title}</h3>
                  <span className="teacher-session-id">{lecture.session_id}</span>
                </div>
                <span className={`status-badge ${lecture.status}`}>{lecture.status}</span>
              </header>

              <div className="teacher-lecture-facts">
                <div><span>Date</span><strong>{formatDate(lecture.lecture_date)}</strong></div>
                <div><span>Start</span><strong>{formatTime(lecture.start_time)}</strong></div>
                <div><span>End</span><strong>{formatTime(lecture.end_time)}</strong></div>
                <div><span>Duration</span><strong>{formatDuration(lecture.duration_seconds)}</strong></div>
                <div><span>Students</span><strong>{lecture.students_attended}</strong></div>
                <div><span>Questions</span><strong>{lecture.questions_asked}</strong></div>
              </div>

              <div className="teacher-lecture-details-grid">
                <section aria-labelledby={`topics-${lecture.session_id}`}>
                  <h4 id={`topics-${lecture.session_id}`}>Detected topics</h4>
                  {lecture.detected_topics.length > 0 ? (
                    <ul className="teacher-topic-tags">
                      {lecture.detected_topics.map((topic) => <li key={topic}>{topic}</li>)}
                    </ul>
                  ) : <p>No data</p>}
                </section>

                <section aria-labelledby={`usage-${lecture.session_id}`}>
                  <h4 id={`usage-${lecture.session_id}`}>Accessibility usage</h4>
                  <ul className="teacher-usage-list">
                    {ACCESSIBILITY_MODES.map(([mode, label]) => (
                      <li key={mode}>
                        <span>{label}</span>
                        <strong>{lecture.accessibility_usage[mode]}</strong>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
            </article>
          ))}
          </div>
        </div>
      )}
    </section>
  )
}
