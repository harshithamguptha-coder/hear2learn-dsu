function formatDuration(seconds) {
  const totalMinutes = Math.max(0, Math.floor(Number(seconds || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function MyLectures({ lectures, loading, error }) {
  return (
    <section className="my-lectures-card" aria-labelledby="my-lectures-title">
      <div className="my-lectures-heading">
        <div>
          <p className="notes-kicker">Personal classroom record</p>
          <h2 id="my-lectures-title">My Lectures</h2>
        </div>
        <span className="history-count">{lectures.length} recorded</span>
      </div>
      {loading && <p className="history-message">Loading your lecture history…</p>}
      {error && <p className="message error" role="alert">{error}</p>}
      {!loading && !error && lectures.length === 0 && (
        <p className="history-message">Lectures you join will appear here.</p>
      )}
      {!loading && !error && lectures.length > 0 && (
        <ul className="my-lectures-list">
          {lectures.map((lecture) => (
            <li key={lecture.session_id} className="my-lecture-item">
              <div className="my-lecture-main">
                <strong>{lecture.title}</strong>
                <span>{lecture.teacher}</span>
              </div>
              <div className="my-lecture-details">
                <span>{formatDate(lecture.lecture_date)}</span>
                <span>{formatDuration(lecture.duration_seconds)}</span>
                <span className={`attendance-status ${lecture.status}`}>
                  {lecture.status === 'in_progress' ? 'In progress' : 'Attended'}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
