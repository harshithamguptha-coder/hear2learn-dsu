import StatusBadge from './StatusBadge'

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDuration(seconds) {
  const totalMinutes = Math.max(0, Math.floor(Number(seconds || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function LectureCard({ lecture, onAction, actionLabel = 'Open lecture' }) {
  const isActive = lecture.status === 'active' || lecture.status === 'in_progress'
  return (
    <article className={`lecture-card ${isActive ? 'is-live' : ''}`}>
      <div className="lecture-card-main">
        <div className="lecture-card-title-row">
          <div>
            <p className="lecture-card-kicker">{isActive ? 'Live classroom' : 'Lecture record'}</p>
            <h3>{lecture.title || 'Untitled Lecture'}</h3>
          </div>
          <StatusBadge status={lecture.status} attendance={lecture.status === 'in_progress' || lecture.status === 'attended'} />
        </div>
        <div className="lecture-card-meta">
          <span>◷ {formatDate(lecture.lecture_date)}</span>
          <span>◷ {formatDuration(lecture.duration_seconds)}</span>
          {lecture.teacher && <span>◎ {lecture.teacher}</span>}
          {typeof lecture.students_attended === 'number' && <span>♙ {lecture.students_attended} students</span>}
          {typeof lecture.questions_asked === 'number' && <span>？ {lecture.questions_asked} questions</span>}
        </div>
        {lecture.session_id && <code className="session-code">{lecture.session_id}</code>}
      </div>
      {onAction && (
        <button className="secondary-button lecture-card-action" type="button" onClick={() => onAction(lecture)}>
          {actionLabel}
          <span aria-hidden="true">→</span>
        </button>
      )}
    </article>
  )
}
