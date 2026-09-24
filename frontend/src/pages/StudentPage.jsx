import { useState } from 'react'

import { getSession } from '../api/client'
import TranscriptView from '../components/TranscriptView'
import { useSessionStream } from '../hooks/useSessionStream'

export default function StudentPage() {
  const [input, setInput] = useState('')
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [joining, setJoining] = useState(false)
  const [translationLanguage, setTranslationLanguage] = useState('en')
  const { transcript, connectionState } = useSessionStream(session?.session_id)

  async function handleJoin(event) {
    event.preventDefault()
    const sessionId = input.trim().toUpperCase()
    if (!sessionId) return

    setJoining(true)
    setError('')
    setSession(null)
    try {
      setSession(await getSession(sessionId))
    } catch (requestError) {
      setError(
        requestError.status === 404
          ? 'We could not find that lecture. Check the session ID and try again.'
          : `Could not join the lecture: ${requestError.message}`,
      )
    } finally {
      setJoining(false)
    }
  }

  const connectionLabel = {
    idle: 'Not connected',
    connecting: 'Connecting…',
    connected: 'Live connection',
    reconnecting: 'Reconnecting…',
  }[connectionState]

  return (
    <main className="shell page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Student workspace</p>
          <h1>Join a live lecture</h1>
          <p>Enter the session ID from your teacher. No account is needed.</p>
        </div>
        <span className="page-number" aria-hidden="true">02</span>
      </div>

      <section className="join-card" aria-label="Join a lecture">
        <form onSubmit={handleJoin}>
          <label htmlFor="session-id">Lecture session ID</label>
          <div className="join-row">
            <input
              id="session-id"
              name="session-id"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="For example: 9A7F3C21"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck="false"
              maxLength="16"
              aria-describedby="session-help"
            />
            <button className="primary-button" type="submit" disabled={joining}>
              {joining ? 'Joining…' : 'Join Lecture'}
            </button>
          </div>
          <p id="session-help">Session IDs are made of letters and numbers.</p>
        </form>
        {error && <p className="message error" role="alert">{error}</p>}
      </section>

      {session && (
        <section className="joined-session" aria-labelledby="joined-title">
          <div>
            <p className="eyebrow">You are in</p>
            <h2 id="joined-title">Lecture {session.session_id}</h2>
          </div>
          <div className="language-control">
            <label htmlFor="translation-language">Translation language</label>
            <select
              id="translation-language"
              value={translationLanguage}
              onChange={(event) => setTranslationLanguage(event.target.value)}
              aria-describedby="translation-help"
            >
              <option value="en">English (original)</option>
              <option value="kn">Kannada</option>
              <option value="hi">Hindi</option>
            </select>
            <small id="translation-help">The original English always stays visible.</small>
          </div>
          <span className="connection-state" role="status">
            <span aria-hidden="true" /> {connectionLabel}
          </span>
          {session.status === 'ended' && (
            <p className="message info">This lecture has ended. The saved transcript is still available.</p>
          )}
        </section>
      )}

      {session ? (
        <TranscriptView
          items={transcript}
          emptyText="The transcript will appear here as soon as the teacher starts speaking."
          sessionId={session.session_id}
          translationLanguage={translationLanguage}
        />
      ) : (
        <div className="waiting-card" aria-hidden="true">
          <span>Join a lecture to see its live transcript.</span>
        </div>
      )}
    </main>
  )
}
