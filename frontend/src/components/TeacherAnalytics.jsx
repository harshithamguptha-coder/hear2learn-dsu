import { useEffect, useState } from 'react'

import { getTeacherDashboard } from '../api/client'
import EmptyState from './EmptyState'
import StatusBadge from './StatusBadge'

const MODES = [
  ['standard', 'Standard', 'Aa'],
  ['simplified', 'Simplified', '✦'],
  ['translation', 'Translation', '文'],
  ['sign_support', 'Sign Support', '🤟'],
]

function formatDuration(seconds) {
  const totalMinutes = Math.max(0, Math.floor(Number(seconds || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

function formatDate(value) {
  if (!value) return 'No data'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function TeacherAnalytics({ token, refreshKey = 0 }) {
  const [dashboard, setDashboard] = useState({ total_lectures: 0, lectures: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getTeacherDashboard(token)
      .then((data) => { if (!cancelled) setDashboard(data) })
      .catch((requestError) => { if (!cancelled) setError(`Analytics are unavailable: ${requestError.message}`) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, refreshKey])

  const lectures = dashboard.lectures || []
  const studentsReached = lectures.reduce((total, lecture) => total + Number(lecture.students_attended || 0), 0)
  const questionsAsked = lectures.reduce((total, lecture) => total + Number(lecture.questions_asked || 0), 0)
  const topics = [...new Set(lectures.flatMap((lecture) => lecture.detected_topics || []))]

  return (
    <div className="view-stack">
      <section className="page-intro">
        <div>
          <p className="eyebrow">Real classroom signals</p>
          <h1>Lecture analytics</h1>
          <p>Understand how your lectures are landing with stored attendance, questions, topics, and accessibility usage.</p>
        </div>
        <StatusBadge status="inactive" label={loading ? 'SYNCING' : 'SYNCED'} />
      </section>
      {error && <p className="message error" role="alert">{error}</p>}
      <div className="analytics-summary-grid">
        <article className="analytics-summary-card"><span>Total lectures</span><strong>{dashboard.total_lectures}</strong><small>Persistent records</small></article>
        <article className="analytics-summary-card"><span>Students reached</span><strong>{studentsReached}</strong><small>Attendance entries</small></article>
        <article className="analytics-summary-card"><span>Questions asked</span><strong>{questionsAsked}</strong><small>Lecture questions</small></article>
        <article className="analytics-summary-card"><span>Topics detected</span><strong>{topics.length}</strong><small>Unique stored topics</small></article>
      </div>
      {loading && <div className="loading-card" role="status">Loading lecture analytics…</div>}
      {!loading && !error && lectures.length === 0 && <EmptyState icon="▥" title="No data yet" description="Analytics will appear after you start and end a lecture with classroom activity." />}
      {!loading && !error && lectures.length > 0 && (
        <div className="analytics-card-list">
          {lectures.map((lecture) => (
            <article className="analytics-card" key={lecture.session_id}>
              <div className="analytics-card-header">
                <div><p className="eyebrow">Lecture overview</p><h2>{lecture.title}</h2><span className="session-code">{lecture.session_id}</span></div>
                <StatusBadge status={lecture.status} />
              </div>
              <div className="analytics-facts">
                <div><span>Date</span><strong>{formatDate(lecture.lecture_date)}</strong></div>
                <div><span>Duration</span><strong>{formatDuration(lecture.duration_seconds)}</strong></div>
                <div><span>Students attended</span><strong>{lecture.students_attended}</strong></div>
                <div><span>Questions asked</span><strong>{lecture.questions_asked}</strong></div>
              </div>
              <div className="analytics-detail-grid">
                <section><h3>Topics detected</h3>{lecture.detected_topics?.length ? <div className="topic-tags">{lecture.detected_topics.map((topic) => <span key={topic}>{topic}</span>)}</div> : <p className="muted-copy">No data yet</p>}</section>
                <section><h3>Accessibility usage</h3><div className="usage-grid">{MODES.map(([key, label, icon]) => <div key={key}><span aria-hidden="true">{icon}</span><span>{label}</span><strong>{lecture.accessibility_usage?.[key] ?? 0}</strong></div>)}</div></section>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
