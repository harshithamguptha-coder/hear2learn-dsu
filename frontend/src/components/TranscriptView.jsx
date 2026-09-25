import { useEffect, useRef } from 'react'

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
  isLive = true,
  id = '',
  tabIndex = -1,
  className = '',
}) {
  const transcriptListRef = useRef(null)
  const latestItem = items[items.length - 1]

  useEffect(() => {
    if (!transcriptListRef.current || !latestItem?.id) return
    transcriptListRef.current.scrollTo({ top: transcriptListRef.current.scrollHeight, behavior: 'smooth' })
  }, [latestItem?.id, items.length])

  return (
    <section id={id || undefined} tabIndex={tabIndex} className={`transcript-panel ${className}`.trim()} aria-labelledby={`${id || 'transcript'}-title`}>
      <div className="panel-heading">
        <h2 id={`${id || 'transcript'}-title`}>{isLive ? 'Live captions' : 'Lecture captions'}</h2>
        <span className={`live-label ${isLive ? 'is-live' : 'is-ended'}`}><span aria-hidden="true" /> {isLive ? 'LIVE' : 'ENDED'}</span>
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
        <ol className="transcript-list" ref={transcriptListRef} aria-live="polite" aria-relevant="additions">
          {items.map((item, index) => (
            <li key={item.id} className={index === items.length - 1 ? 'is-latest' : ''}>
              <time dateTime={item.created_at}>{formatTime(item.created_at)}</time>
              <div className="transcript-text">
                <p lang="en">{item.text}</p>
                {index === items.length - 1 && <span className="latest-caption-label">Newest caption</span>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
