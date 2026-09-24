import { useState } from 'react'
import { askLectureQuestion } from '../api/client'

const QUICK_SUGGESTIONS = [
  'Explain that simply',
  'Give an example',
  'What formula was mentioned?',
  'What are the key points?',
]

export default function StructuredLectureView({
  structuredData,
  loading,
  error,
  sessionId,
  qaResult: externalQaResult,
  setQaResult: externalSetQaResult,
  questionInput: externalQuestionInput,
  setQuestionInput: externalSetQuestionInput,
  conversationId: externalConversationId,
  setConversationId: externalSetConversationId,
  conversationMessages: externalConversationMessages,
  setConversationMessages: externalSetConversationMessages,
}) {
  const [internalQuestionInput, setInternalQuestionInput] = useState('')
  const [internalQaResult, setInternalQaResult] = useState(null)
  const [internalConversationId, setInternalConversationId] = useState(null)
  const [internalMessages, setInternalMessages] = useState([])
  const [qaLoading, setQaLoading] = useState(false)
  const [qaError, setQaError] = useState('')

  const questionInput = externalQuestionInput !== undefined ? externalQuestionInput : internalQuestionInput
  const setQuestionInput = externalSetQuestionInput || setInternalQuestionInput
  const qaResult = externalQaResult !== undefined ? externalQaResult : internalQaResult
  const setQaResult = externalSetQaResult || setInternalQaResult
  const conversationId = externalConversationId !== undefined ? externalConversationId : internalConversationId
  const setConversationId = externalSetConversationId || setInternalConversationId
  const messages = externalConversationMessages !== undefined ? externalConversationMessages : internalMessages
  const setMessages = externalSetConversationMessages || setInternalMessages

  async function handleAskQuestion(e, explicitQuestion = null) {
    if (e && e.preventDefault) e.preventDefault()
    const q = (explicitQuestion || questionInput).trim()
    if (!q || !sessionId || qaLoading) return

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsg = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      role: 'user',
      content: q,
      timestamp: nowStr,
    }

    setMessages((prev) => [...prev, userMsg])
    setQuestionInput('')
    setQaLoading(true)
    setQaError('')

    try {
      const res = await askLectureQuestion(sessionId, q, conversationId)
      if (res.conversation_id && res.conversation_id !== conversationId) {
        setConversationId(res.conversation_id)
      }
      const assistantMsg = {
        id: `ast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        role: 'assistant',
        content: res.answer,
        sources: res.sources || [],
        lecture_grounded: Boolean(res.lecture_grounded),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setQaResult(res)
    } catch (err) {
      setQaError(err.message || 'Unable to answer this question right now.')
    } finally {
      setQaLoading(false)
    }
  }

  function handleResetConversation() {
    setMessages([])
    setConversationId(null)
    setQaResult(null)
    setQaError('')
    setQuestionInput('')
  }

  const {
    topic,
    clean_text,
    key_points = [],
    concepts = [],
    technical_terms = [],
    numbers = [],
    formulas = [],
    speaker_segments = [],
    topic_history = [],
    important_points = [],
    definitions = [],
    examples = [],
    important_moments = [],
  } = structuredData || {}

  const getSpeakerBadge = (speaker) => {
    switch (speaker) {
      case 'Teacher':
        return {
          icon: '👨‍🏫',
          label: 'Teacher',
          className: 'speaker-badge teacher',
        }
      case 'Student':
        return {
          icon: '🎓',
          label: 'Student',
          className: 'speaker-badge student',
        }
      default:
        return {
          icon: '👤',
          label: 'Unknown',
          className: 'speaker-badge unknown',
        }
    }
  }

  return (
    <section className="structured-lecture-container" aria-label="Structured Lecture Notes">
      <header className="structured-header">
        <div className="structured-title-group">
          <div className="structured-eyebrow-row">
            <span className="badge ai-badge">AI Classroom Intelligence</span>
            {loading && <span className="structuring-indicator" role="status">Updating notes…</span>}
          </div>
          {topic ? (
            <h2 className="lecture-topic">{topic}</h2>
          ) : (
            <h2 className="lecture-topic placeholder">Live Lecture Intelligence</h2>
          )}
        </div>

        {/* Dynamic Topic History / Progression */}
        {topic_history && topic_history.length > 0 && (
          <nav className="topic-progression-bar" aria-label="Lecture Topic Progression">
            <span className="topic-progression-label">Topics:</span>
            <div className="topic-progression-pills">
              {topic_history.map((seg, idx) => {
                const isCurrent = idx === topic_history.length - 1
                return (
                  <span
                    key={idx}
                    className={`topic-pill ${isCurrent ? 'active' : 'completed'}`}
                    title={isCurrent ? 'Current active topic' : 'Previously discussed topic'}
                  >
                    {seg.topic}
                    {isCurrent && <span className="active-dot" aria-hidden="true" />}
                  </span>
                )
              })}
            </div>
          </nav>
        )}
      </header>

      {error && (
        <div className="structured-banner warning" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Speaker Attribution / Classroom Dialogue */}
      {speaker_segments && speaker_segments.length > 0 && (
        <article className="structured-section speaker-section" aria-labelledby="speakers-title">
          <div className="section-title-row">
            <h3 id="speakers-title">Speaker Attribution</h3>
            <span className="section-meta-pill">
              {speaker_segments.length} segment{speaker_segments.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="speaker-segments-list">
            {speaker_segments.map((seg, idx) => {
              const badge = getSpeakerBadge(seg.speaker)
              return (
                <div key={idx} className={`speaker-segment-card ${seg.speaker.toLowerCase()}`}>
                  <div className="speaker-segment-header">
                    <span className={badge.className}>
                      <span aria-hidden="true">{badge.icon}</span> {badge.label}
                    </span>
                    {seg.timestamp && (
                      <time className="speaker-timestamp">{seg.timestamp}</time>
                    )}
                  </div>
                  <p className="speaker-segment-text">{seg.text}</p>
                </div>
              )
            })}
          </div>
        </article>
      )}

      {/* Important Emphasized Points */}
      {important_points && important_points.length > 0 && (
        <article className="structured-section important-points-section" aria-labelledby="important-points-title">
          <div className="section-title-row">
            <h3 id="important-points-title">
              <span className="section-title-icon" aria-hidden="true">💡</span> Important Points
            </h3>
            <span className="section-meta-pill highlight">Teacher Emphasized</span>
          </div>
          <ul className="important-points-list">
            {important_points.map((point, idx) => (
              <li key={idx} className="important-point-item">
                <span className="important-bullet" aria-hidden="true">★</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </article>
      )}

      {/* Clean Educational Text */}
      {clean_text && (
        <article className="structured-section clean-text-section" aria-labelledby="clean-text-title">
          <h3 id="clean-text-title">Clean Lecture Summary</h3>
          <div className="clean-lecture-body">
            {clean_text.split('\n\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>
        </article>
      )}

      {/* Definitions */}
      {definitions && definitions.length > 0 && (
        <article className="structured-section definitions-section" aria-labelledby="definitions-title">
          <div className="section-title-row">
            <h3 id="definitions-title">
              <span className="section-title-icon" aria-hidden="true">📖</span> Definitions
            </h3>
            <span className="section-meta-pill">{definitions.length} term{definitions.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="definitions-grid">
            {definitions.map((item, idx) => (
              <div key={idx} className="definition-card">
                <strong className="definition-term">{item.term}</strong>
                <p className="definition-desc">{item.definition}</p>
              </div>
            ))}
          </div>
        </article>
      )}

      {/* Real-World Examples */}
      {examples && examples.length > 0 && (
        <article className="structured-section examples-section" aria-labelledby="examples-title">
          <div className="section-title-row">
            <h3 id="examples-title">
              <span className="section-title-icon" aria-hidden="true">🔬</span> Real-World Examples
            </h3>
            <span className="section-meta-pill">{examples.length} example{examples.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="examples-grid">
            {examples.map((item, idx) => (
              <div key={idx} className="example-card">
                <span className="example-concept-pill">{item.concept}</span>
                <p className="example-text">{item.example}</p>
              </div>
            ))}
          </div>
        </article>
      )}

      {/* Key Takeaways */}
      {key_points && key_points.length > 0 && (
        <article className="structured-section key-points-section" aria-labelledby="key-points-title">
          <h3 id="key-points-title">Key Takeaways</h3>
          <ul className="key-points-list">
            {key_points.map((point, idx) => (
              <li key={idx} className="key-point-item">
                <span className="bullet-point-icon" aria-hidden="true">✓</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </article>
      )}

      {/* Educational Concepts & Technical Terms */}
      {((concepts && concepts.length > 0) || (technical_terms && technical_terms.length > 0)) && (
        <div className="terms-concepts-grid">
          {concepts && concepts.length > 0 && (
            <article className="structured-section concepts-section" aria-labelledby="concepts-title">
              <h3 id="concepts-title">Core Concepts</h3>
              <div className="tags-container">
                {concepts.map((concept, idx) => (
                  <span key={idx} className="tag concept-tag">
                    {concept}
                  </span>
                ))}
              </div>
            </article>
          )}

          {technical_terms && technical_terms.length > 0 && (
            <article className="structured-section terms-section" aria-labelledby="terms-title">
              <h3 id="terms-title">Technical Terms</h3>
              <div className="tags-container">
                {technical_terms.map((term, idx) => (
                  <span key={idx} className="tag term-tag">
                    {term}
                  </span>
                ))}
              </div>
            </article>
          )}
        </div>
      )}

      {/* Numbers & Formulas */}
      {((numbers && numbers.length > 0) || (formulas && formulas.length > 0)) && (
        <div className="numbers-formulas-grid">
          {numbers && numbers.length > 0 && (
            <article className="structured-section numbers-section" aria-labelledby="numbers-title">
              <h3 id="numbers-title">Key Numbers & Metrics</h3>
              <div className="tags-container">
                {numbers.map((num, idx) => (
                  <span key={idx} className="tag number-tag">
                    {num}
                  </span>
                ))}
              </div>
            </article>
          )}

          {formulas && formulas.length > 0 && (
            <article className="structured-section formulas-section" aria-labelledby="formulas-title">
              <h3 id="formulas-title">Formulas & Equations</h3>
              <div className="formulas-container">
                {formulas.map((formula, idx) => (
                  <code key={idx} className="formula-box">
                    {formula}
                  </code>
                ))}
              </div>
            </article>
          )}
        </div>
      )}

      {/* Important Review Moments */}
      {important_moments && important_moments.length > 0 && (
        <article className="structured-section moments-section" aria-labelledby="moments-title">
          <div className="section-title-row">
            <h3 id="moments-title">
              <span className="section-title-icon" aria-hidden="true">⭐</span> Key Review Moments
            </h3>
            <span className="section-meta-pill">Revision Log</span>
          </div>
          <div className="moments-list">
            {important_moments.map((moment, idx) => (
              <div key={idx} className={`moment-card type-${moment.type || 'general'}`}>
                <div className="moment-card-header">
                  <span className={`moment-type-badge ${moment.type || 'general'}`}>
                    {moment.type ? moment.type.replace('_', ' ') : 'NOTE'}
                  </span>
                  {moment.timestamp && (
                    <time className="moment-timestamp">{moment.timestamp}</time>
                  )}
                </div>
                <p className="moment-content">{moment.content}</p>
              </div>
            ))}
          </div>
        </article>
      )}

      {/* Lecture-Grounded AI Assistant (Multi-turn) */}
      <article className="structured-section qa-section" aria-labelledby="qa-title">
        <div className="qa-section-header">
          <div>
            <div className="qa-title-row">
              <h3 id="qa-title">Lecture Assistant</h3>
              {messages.length > 0 && (
                <span className="qa-turn-counter">
                  {messages.filter((m) => m.role === 'user').length} question{messages.filter((m) => m.role === 'user').length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            <p className="qa-section-desc">
              Ask questions and follow-ups. Grounded strictly in this lecture session.
            </p>
          </div>
          <div className="qa-header-actions">
            <span className="badge grounded-badge" title="Grounded in current session only">
              Lecture-Grounded
            </span>
            {messages.length > 0 && (
              <button
                type="button"
                className="secondary-button new-conversation-btn"
                onClick={handleResetConversation}
                title="Start a fresh conversation thread for this lecture"
              >
                + New Chat
              </button>
            )}
          </div>
        </div>

        {/* Multi-turn Chat Thread */}
        <div className="qa-chat-thread" role="log" aria-live="polite">
          {messages.length === 0 ? (
            <div className="qa-empty-thread">
              <span className="qa-empty-icon" aria-hidden="true">💬</span>
              <p>Ask anything about this lecture! Follow-ups like <em>"Explain that simply"</em> or <em>"Give an example"</em> are understood in context.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`qa-chat-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`}
              >
                <div className="bubble-header">
                  <span className="bubble-author">
                    {msg.role === 'user' ? '👤 You' : '🤖 Lecture Assistant'}
                  </span>
                  {msg.role === 'assistant' && (
                    msg.lecture_grounded ? (
                      <span className="qa-grounded-pill verified">✓ In Lecture</span>
                    ) : (
                      <span className="qa-grounded-pill unverified">Not In Lecture</span>
                    )
                  )}
                  {msg.timestamp && (
                    <span className="bubble-time">{msg.timestamp}</span>
                  )}
                </div>

                <div className="bubble-content">
                  <p className="bubble-text">{msg.content}</p>
                </div>

                {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                  <div className="qa-sources-block">
                    <span className="qa-sources-title">Based on lecture:</span>
                    <ul className="qa-sources-list">
                      {msg.sources.map((src, sIdx) => (
                        <li key={sIdx} className="qa-source-item">
                          <blockquote className="qa-source-quote">"{src}"</blockquote>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))
          )}

          {qaLoading && (
            <div className="qa-chat-bubble assistant-bubble loading" role="status">
              <div className="bubble-header">
                <span className="bubble-author">🤖 Lecture Assistant</span>
                <span className="spinner-dot" aria-hidden="true" />
              </div>
              <p className="bubble-text">Thinking about this lecture…</p>
            </div>
          )}
        </div>

        {qaError && (
          <div className="qa-error-box" role="alert">
            <span>{qaError}</span>
          </div>
        )}

        {/* Quick Follow-Up Chips */}
        <div className="qa-suggestions-row" aria-label="Suggested follow-up questions">
          <span className="suggestions-label">Suggestions:</span>
          <div className="suggestions-pills">
            {QUICK_SUGGESTIONS.map((sug, idx) => (
              <button
                key={idx}
                type="button"
                className="suggestion-pill-btn"
                disabled={qaLoading || !sessionId}
                onClick={() => handleAskQuestion(null, sug)}
              >
                {sug}
              </button>
            ))}
          </div>
        </div>

        <form className="qa-form" onSubmit={(e) => handleAskQuestion(e)}>
          <div className="qa-input-row">
            <input
              type="text"
              className="qa-input"
              value={questionInput}
              onChange={(e) => setQuestionInput(e.target.value)}
              placeholder="Ask a question or follow-up (e.g. 'Explain that simply' or 'Give an example')…"
              disabled={qaLoading || !sessionId}
              aria-label="Ask a question or follow-up about this lecture"
            />
            <button
              type="submit"
              className="primary-button qa-button"
              disabled={qaLoading || !questionInput.trim() || !sessionId}
            >
              {qaLoading ? 'Thinking…' : 'Send'}
            </button>
          </div>
        </form>
      </article>
    </section>
  )
}
