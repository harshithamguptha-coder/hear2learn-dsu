import EmptyState from './EmptyState'
import LectureCard from './LectureCard'
import StatCard from './StatCard'

export default function StudentOverview({ user, lectures, loading, error, session, onViewChange, onViewLecture }) {
  const attendedCount = lectures.length
  const activeLecture = session?.status === 'active' ? session : null
  const recentLectures = lectures.slice(0, 3)

  return (
    <div className="view-stack">
      <section className="welcome-banner student-welcome">
        <div>
          <p className="eyebrow">Your learning space</p>
          <h1>Welcome back, {user?.name || 'learner'}.</h1>
          <p>Choose the way you want to learn, then join a live classroom when you are ready.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => onViewChange('join')}>＋ Join a lecture</button>
      </section>

      <div className="stats-grid" aria-label="Student summary">
        <StatCard icon="▤" label="Lectures attended" value={attendedCount} detail="Personal history" tone="blue" />
        <StatCard icon="▥" label="Study packs" value="—" detail="Not tracked yet" tone="lilac" />
        <StatCard icon="？" label="Questions asked" value="—" detail="Not tracked yet" tone="amber" />
        <StatCard icon="◉" label="Current lecture" value={activeLecture ? 'Live' : '—'} detail={activeLecture ? activeLecture.title : 'No active session'} tone="mint" />
      </div>

      <section className="content-section" aria-labelledby="student-recent-title">
        <div className="section-heading-row">
          <div><p className="eyebrow">Your classroom record</p><h2 id="student-recent-title">My recent lectures</h2></div>
          {lectures.length > 0 && <button className="text-button" type="button" onClick={() => onViewChange('lectures')}>View all <span aria-hidden="true">→</span></button>}
        </div>
        {error && <p className="message error" role="alert">{error}</p>}
        {loading && <div className="loading-card" role="status">Loading your lecture history…</div>}
        {!loading && !error && recentLectures.length === 0 && (
          <EmptyState icon="▤" title="No lectures yet" description="Lectures you join will appear here with your real attendance history." action={<button className="primary-button" type="button" onClick={() => onViewChange('join')}>Join your first lecture</button>} />
        )}
        {!loading && !error && recentLectures.length > 0 && (
          <div className="lecture-list">{recentLectures.map((lecture) => <LectureCard key={lecture.session_id} lecture={lecture} onAction={onViewLecture} actionLabel="View lecture" />)}</div>
        )}
      </section>
    </div>
  )
}
