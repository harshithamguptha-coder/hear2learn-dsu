import { useAuth } from '../context/AuthContext'
import { useEffect, useRef, useState } from 'react'

import { getLectureNotes, getSession, structureTranscript } from '../api/client'
import LectureNotes from '../components/LectureNotes'
import StructuredLectureView from '../components/StructuredLectureView'
import TranscriptView from '../components/TranscriptView'
import { useLectureContext } from '../context/LectureContext'
import { useSessionStream } from '../hooks/useSessionStream'

export default function StudentPage() {
  const { user } = useAuth()
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
  const [translationLanguage, setTranslationLanguage] = useState('en')
  const [notes, setNotes] = useState(null)
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')

  const { transcript, connectionState, sessionEnded } = useSessionStream(
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

  useEffect(() => {
    if (sessionEnded) {
      setSession((current) => (
        current ? { ...current, status: 'ended' } : current
      ))
    }
  }, [sessionEnded, setSession])

  useEffect(() => {
    const sessionId = session?.session_id
    const shouldLoad = session?.status === 'ended' || sessionEnded
    if (!sessionId || !shouldLoad || notes) return undefined

    let cancelled = false
    setNotesLoading(true)
    setNotesError('')
    getLectureNotes(sessionId)
      .then((generatedNotes) => {
        if (!cancelled) setNotes(generatedNotes)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setNotesError(`Lecture notes could not be loaded: ${requestError.message}`)
        }
      })
      .finally(() => {
        if (!cancelled) setNotesLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [notes, session?.session_id, session?.status, sessionEnded])

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
    setNotes(null)
    setNotesError('')

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
          <p>Welcome, {user?.name}. Enter the session ID from your teacher to join the live classroom.</p>
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
              <option value="te">Telugu</option>
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
        <div className="student-lecture-layout">
          {(notes || notesLoading || notesError) && (
            <LectureNotes notes={notes} loading={notesLoading} error={notesError} />
          )}

          <TranscriptView
            items={transcript}
            emptyText="The transcript will appear here as soon as the teacher starts speaking."
            sessionId={session.session_id}
            translationLanguage={translationLanguage}
          />

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
        </div>
      ) : (
        <div className="waiting-card" aria-hidden="true">
          <span>Join a lecture to see its live transcript.</span>
        </div>
      )}
    </main>
  )
}
