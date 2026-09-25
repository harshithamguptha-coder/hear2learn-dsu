import { useEffect, useState } from 'react'

import { getTeacherDashboard } from '../api/client'
import EmptyState from './EmptyState'
import LectureCard from './LectureCard'

export default function TeacherLectureList({ token, refreshKey = 0, onViewLecture }) {
  const [dashboard, setDashboard] = useState({ lectures: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getTeacherDashboard(token)
      .then((data) => { if (!cancelled) setDashboard(data) })
      .catch((requestError) => { if (!cancelled) setError(`Lecture records are unavailable: ${requestError.message}`) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, refreshKey])

  const lectures = dashboard.lectures || []
  return (
    <div className="view-stack">
      <section className="page-intro"><div><p className="eyebrow">Persisted classroom activity</p><h1>Recent lectures</h1><p>Your lecture history, attendance, and live status come directly from your teacher account.</p></div><span className="count-pill">{dashboard.total_lectures ?? lectures.length} total</span></section>
      {error && <p className="message error" role="alert">{error}</p>}
      {loading && <div className="loading-card" role="status">Loading your lecture records…</div>}
      {!loading && !error && lectures.length === 0 && <EmptyState icon="▤" title="No lectures yet" description="Your created lectures will appear here after you start your first class." />}
      {!loading && !error && lectures.length > 0 && <div className="lecture-list">{lectures.map((lecture) => <LectureCard key={lecture.session_id} lecture={lecture} onAction={onViewLecture} actionLabel="Open lecture" />)}</div>}
    </div>
  )
}
