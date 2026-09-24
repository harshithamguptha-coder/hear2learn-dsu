import { useEffect, useRef, useState } from 'react'

import { getSession, structureTranscript } from '../api/client'
import StructuredLectureView from '../components/StructuredLectureView'
import TranscriptView from '../components/TranscriptView'
import { useLectureContext } from '../context/LectureContext'
import { useSessionStream } from '../hooks/useSessionStream'

export default function StudentPage() {
  const {
    studentInput: input,
    setStudentInput: setInput,
    studentSession: session,
    setStudentSession: setSession,
    studentTranscript,
    setStudentTranscript,
    studentStructuredData: structuredData,
    setStudentStructuredData: setStructuredData,
    studentStructureError: structureError,
    setStudentStructureError: setStructureError,
    studentQaResult: qaResult,
    setStudentQaResult: setQaResult,
    studentQuestionInput: questionInput,
    setStudentQuestionInput: setQuestionInput,
    studentLastStructuredText,
    setStudentLastStructuredText,
    teacherSession,
  } = useLectureContext()

  const [error, setError] = useState('')
  const [joining, setJoining] = useState(false)
  const [structuring, setStructuring] = useState(false)
  const { transcript, connectionState } = useSessionStream(
    session?.session_id,
    studentTranscript,
    setStudentTranscript,
  )
  const lastStructuredTextRef = useRef(studentLastStructuredText)

  // If student is not connected and teacher has an active session, auto-connect for seamless switching
  useEffect(() => {
    if (!session && teacherSession?.session_id) {
      setInput(teacherSession.session_id)
      setSession(teacherSession)
    }
  }, [session, teacherSession, setInput, setSession])

  async function handleJoin(event) {
    event.preventDefault()
    const sessionId = input.trim().toUpperCase()
    if (!sessionId) return

    setJoining(true)
    setError('')
    setSession(null)
    setStudentTranscript([])
    setStructuredData(null)
    setStructureError('')
    setQaResult(null)
    setStudentLastStructuredText('')
    lastStructuredTextRef.current = ''

    try {
      const foundSession = await getSession(sessionId)
      setSession(foundSession)
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

  // 1500ms debounced transcript structuring
  useEffect(() => {
    if (!session?.session_id) return

    const fullText = transcript.map((item) => item.text).join(' ').trim()
    if (!fullText) return

    if (structuredData && (fullText === lastStructuredTextRef.current || fullText === studentLastStructuredText)) return

    const delay = structuredData ? 1500 : 250
    const timer = setTimeout(async () => {
      setStructuring(true)
      try {
        const result = await structureTranscript(session.session_id, fullText)
        setStructuredData(result)
        lastStructuredTextRef.current = fullText
        setStudentLastStructuredText(fullText)
        setStructureError('')
      } catch (err) {
        setStructureError(err.message || 'Could not update structured lecture notes.')
      } finally {
        setStructuring(false)
      }
    }, delay)

    return () => clearTimeout(timer)
  }, [
    session?.session_id,
    transcript,
    structuredData,
    setStructuredData,
    setStructureError,
    studentLastStructuredText,
    setStudentLastStructuredText,
  ])

  const connectionLabel = {
    idle: 'Not connected',
    connecting: 'Connecting…',
    connected: 'Live connection',
    reconnecting: 'Reconnecting…',
    ended: 'Lecture finished',
  }[connectionState] || 'Not connected'

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
          <span className="connection-state" role="status">
            <span aria-hidden="true" /> {connectionLabel}
          </span>
          {session.status === 'ended' && (
            <p className="message info">This lecture has ended. The saved transcript is still available.</p>
          )}
        </section>
      )}

      {session ? (
        <div className="student-lecture-layout">
          <StructuredLectureView
            structuredData={structuredData}
            loading={structuring}
            error={structureError}
            sessionId={session.session_id}
            qaResult={qaResult}
            setQaResult={setQaResult}
            questionInput={questionInput}
            setQuestionInput={setQuestionInput}
          />

          <details className="raw-transcript-details" open={!structuredData}>
            <summary className="raw-transcript-summary">
              <span>Raw Live Transcript</span>
              <span className="raw-transcript-badge">{transcript.length} items</span>
            </summary>
            <TranscriptView
              items={transcript}
              emptyText="The transcript will appear here as soon as the teacher starts speaking."
            />
          </details>
        </div>
      ) : (
        <div className="waiting-card" aria-hidden="true">
          <span>Join a lecture to see its live transcript.</span>
        </div>
      )}
    </main>
  )
}
