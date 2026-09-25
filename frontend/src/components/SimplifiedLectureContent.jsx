import { buildSimplifiedLecture } from '../services/simplifiedLanguage'

export default function SimplifiedLectureContent({
  items,
  structuredData,
  loading = false,
  error = '',
}) {
  const content = buildSimplifiedLecture(items, structuredData)

  return (
    <section className="simplified-lecture-panel" aria-labelledby="simplified-content-title">
      <header className="simplified-lecture-header">
        <div>
          <p className="eyebrow">Simplified view</p>
          <h2 id="simplified-content-title">Lecture in easier language</h2>
        </div>
        <p>Key points first, with important technical terms kept in their original form.</p>
      </header>

      {error && <p className="message error" role="alert">{error}</p>}

      {!content.hasContent ? (
        <div className="empty-state">
          <p>{loading ? 'Preparing an easier-language view…' : 'The simplified view will appear as soon as the teacher starts speaking.'}</p>
        </div>
      ) : (
        <>
          {content.keyPoints.length > 0 && (
            <section className="simplified-section" aria-labelledby="simplified-key-points-title">
              <h3 id="simplified-key-points-title">Key points in plain language</h3>
              <ul className="simplified-key-points">
                {content.keyPoints.map((point, index) => (
                  <li key={`${point}-${index}`}>{point}</li>
                ))}
              </ul>
            </section>
          )}

          {content.text && (
            <section className="simplified-section" aria-labelledby="simplified-summary-title">
              <h3 id="simplified-summary-title">Easy-language summary</h3>
              <p>{content.text}</p>
            </section>
          )}

          {content.technicalTerms.length > 0 && (
            <section className="simplified-section" aria-labelledby="simplified-terms-title">
              <h3 id="simplified-terms-title">Important technical terms</h3>
              <ul className="simplified-technical-terms">
                {content.technicalTerms.map((term) => <li key={term}>{term}</li>)}
              </ul>
            </section>
          )}
        </>
      )}
    </section>
  )
}
