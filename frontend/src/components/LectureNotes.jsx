export default function LectureNotes({ notes, loading, error }) {
  if (loading) {
    return (
      <section className="notes-card" aria-labelledby="notes-title">
        <p className="notes-loading" role="status">Preparing lecture notes…</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="notes-card" aria-labelledby="notes-title">
        <h2 id="notes-title">Lecture Notes</h2>
        <p className="message error" role="alert">{error}</p>
      </section>
    )
  }

  if (!notes) return null

  return (
    <section className="notes-card" aria-labelledby="notes-title">
      <div className="panel-heading">
        <div>
          <span className="notes-kicker">Automatic lecture notes</span>
          <h2 id="notes-title">Lecture Notes</h2>
        </div>
        <span className={`notes-status ${notes.status}`}>
          {notes.status === 'ready' ? 'Ready' : 'More speech needed'}
        </span>
      </div>

      {notes.status === 'too_short' ? (
        <div className="notes-short-message">
          <h3>{notes.title}</h3>
          <p>{notes.message}</p>
          <p>The original transcript is still available below.</p>
        </div>
      ) : (
        <div className="notes-content">
          <section>
            <h3>Lecture title</h3>
            <p className="notes-title-text">{notes.title}</p>
          </section>
          <section>
            <h3>Short summary</h3>
            <p>{notes.summary}</p>
          </section>
          <section>
            <h3>Main topics</h3>
            <ul className="notes-tags">
              {notes.main_topics.map((topic) => <li key={topic}>{topic}</li>)}
            </ul>
          </section>
          <section>
            <h3>Key points</h3>
            <ul>{notes.key_points.map((point) => <li key={point}>{point}</li>)}</ul>
          </section>
          <section>
            <h3>Important terms</h3>
            <ul className="notes-tags">
              {notes.important_terms.map((term) => <li key={term}>{term}</li>)}
            </ul>
          </section>
        </div>
      )}
    </section>
  )
}
