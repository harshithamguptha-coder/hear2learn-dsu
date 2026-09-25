import EmptyState from './EmptyState'
import LectureCard from './LectureCard'

export default function StudentLectureList({ lectures, loading, error, onViewLecture }) {
  return (
    <div className="view-stack">
      <section className="page-intro">
        <div><p className="eyebrow">Personal classroom record</p><h1>My lectures</h1><p>Every lecture below belongs to your account and reflects your actual attendance.</p></div>
        <span className="count-pill">{lectures.length} {lectures.length === 1 ? 'lecture' : 'lectures'}</span>
      </section>
      {error && <p className="message error" role="alert">{error}</p>}
      {loading && <div className="loading-card" role="status">Loading your lecture history…</div>}
      {!loading && !error && lectures.length === 0 && <EmptyState icon="▤" title="No lectures yet" description="Join a live lecture to start building your personal learning history." />}
      {!loading && !error && lectures.length > 0 && <div className="lecture-list">{lectures.map((lecture) => <LectureCard key={lecture.session_id} lecture={lecture} onAction={onViewLecture} actionLabel="View lecture" />)}</div>}
    </div>
  )
}
