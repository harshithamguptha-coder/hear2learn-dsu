import { useEffect, useState } from 'react'

import { getTeacherDashboard } from '../api/client'
import EmptyState from './EmptyState'
import LectureCard from './LectureCard'
import StatCard from './StatCard'

export default function TeacherOverview({ token, refreshKey = 0, onViewChange, onViewLecture }) {
  const [dashboard, setDashboard] = useState({ total_lectures: 0, lectures: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getTeacherDashboard(token)
      .then((data) => { if (!cancelled) setDashboard(data) })
      .catch((requestError) => {
        if (!cancelled) setError(`Dashboard data is unavailable: ${requestError.message}`)
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, refreshKey])

  const lectures = dashboard.lectures || []
  const activeLectures = lectures.filter((lecture) => lecture.status === 'active')
  const studentsReached = lectures.reduce((total, lecture) => total + Number(lecture.students_attended || 0), 0)
  const questionsAnswered = lectures.reduce((total, lecture) => total + Number(lecture.questions_asked || 0), 0)

  return (
    <div className="view-stack">
      <section className="welcome-banner">
        <div>
          <p className="eyebrow">Your teaching studio</p>
          <h1>Make every lecture easier to enter.</h1>
          <p>See what is happening in your classroom, then shape the next learning moment.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => onViewChange('new')}>＋ Start new lecture</button>
      </section>

      <div className="stats-grid" aria-label="Teacher summary">
        <StatCard icon="▤" label="Total lectures" value={dashboard.total_lectures} detail="All time" tone="blue" />
        <StatCard icon="◉" label="Active lecture" value={activeLectures.length} detail={activeLectures.length ? 'Live now' : 'No active session'} tone="mint" />
        <StatCard icon="♙" label="Students reached" value={studentsReached} detail="Across your lectures" tone="lilac" />
        <StatCard icon="？" label="Questions asked" value={questionsAnswered} detail="Stored questions" tone="amber" />
      </div>

      <section className="content-section" aria-labelledby="teacher-recent-title">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">Your classroom record</p>
            <h2 id="teacher-recent-title">Recent lectures</h2>
          </div>
          {lectures.length > 0 && <button className="text-button" type="button" onClick={() => onViewChange('lectures')}>View all <span aria-hidden="true">→</span></button>}
        </div>
        {error && <p className="message error" role="alert">{error}</p>}
        {loading && <div className="loading-card" role="status">Loading your lecture records…</div>}
        {!loading && !error && lectures.length === 0 && (
          <EmptyState
            icon="▤"
            title="No lectures yet"
            description="Start your first live classroom and its real attendance and analytics will appear here."
            action={<button className="primary-button" type="button" onClick={() => onViewChange('new')}>Start a lecture</button>}
          />
        )}
        {!loading && !error && lectures.length > 0 && (
          <div className="lecture-list">
            {lectures.slice(0, 4).map((lecture) => (
              <LectureCard key={lecture.session_id} lecture={lecture} onAction={onViewLecture} actionLabel="View details" />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
