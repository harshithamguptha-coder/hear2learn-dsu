import TranslationLine from './TranslationLine'

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

export default function TranscriptView({
  items,
  interimText = '',
  emptyText,
  sessionId = '',
  translationLanguage = 'en',
}) {
  return (
    <section className="transcript-panel" aria-labelledby="transcript-title">
      <div className="panel-heading">
        <h2 id="transcript-title">Live transcript</h2>
        <span className="live-label"><span aria-hidden="true" /> Live</span>
      </div>

      {interimText && (
        <p className="interim-transcript" aria-label="Speech being recognized">
          {interimText}
        </p>
      )}

      {items.length === 0 ? (
        <div className="empty-state">
          <span aria-hidden="true">Aa</span>
          <p>{emptyText}</p>
        </div>
      ) : (
        <ol className="transcript-list" aria-live="polite" aria-relevant="additions">
          {items.map((item) => (
            <li key={item.id}>
              <time dateTime={item.created_at}>{formatTime(item.created_at)}</time>
              <div className="transcript-text">
                <p lang="en">{item.text}</p>
                <TranslationLine
                  sessionId={sessionId}
                  text={item.text}
                  language={translationLanguage}
                />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
