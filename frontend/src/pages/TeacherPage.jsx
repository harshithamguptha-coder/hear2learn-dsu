import { useCallback, useEffect, useRef, useState } from 'react'

import { createLecture, endSession, saveTranscript } from '../api/client'
import TranscriptView from '../components/TranscriptView'
import { useAuth } from '../context/AuthContext'
import { useLectureContext } from '../context/LectureContext'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

function mergeItem(current, newItem) {
  return current.some((item) => item.id === newItem.id)
    ? current
    : [...current, newItem]
}

export default function TeacherPage() {
  const { user, token } = useAuth()
  const {
    teacherSession: session,
    setTeacherSession: setSession,
    teacherTranscript: transcript,
    setTeacherTranscript: setTranscript,
    setStudentSession,
    setStudentInput,
    setStudentTranscript,
    setStudentStructuredData,
    setStudentStructureError,
    setStudentQaResult,
    setStudentQuestionInput,
    setStudentLastStructuredText,
  } = useLectureContext()

  const [actionError, setActionError] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [copied, setCopied] = useState(false)
  const [manualText, setManualText] = useState('')
  const [lectureTitle, setLectureTitle] = useState('Untitled Lecture')

  const sessionRef = useRef(session)
  useEffect(() => {
    sessionRef.current = session
  }, [session])

  const handleFinalText = useCallback(async (text) => {
    const currentSession = sessionRef.current
    console.log('[Teacher] handleFinalText called with text:', text, 'session:', currentSession)

    if (!currentSession || currentSession.status !== 'active') {
      console.warn('[Teacher] Ignored transcript: no active lecture session.')
      return
    }

    try {
      const savedItem = await saveTranscript(currentSession.session_id, text)
      console.log('[Teacher] Transcript chunk saved to backend:', savedItem)
      setTranscript((current) => mergeItem(current, savedItem))
      setActionError('')
    } catch (error) {
      console.error('[Teacher] Error saving transcript:', error)
      setActionError(`Could not save transcript: ${error.message}`)
    }
  }, [setTranscript])

  const speech = useSpeechRecognition(handleFinalText)

  async function handleStartLecture() {
    setBusyAction('start')
    setActionError('')
    setCopied(false)
    try {
      const newSession = await createLecture(lectureTitle.trim() || 'Untitled Lecture', token)
      console.log('[Teacher] Created new lecture session:', newSession)
      setSession(newSession)
      setTranscript([])
      setStudentSession(newSession)
      setStudentInput(newSession.session_id)
      setStudentTranscript([])
      setStudentStructuredData(null)
      setStudentStructureError('')
      setStudentQaResult(null)
      setStudentQuestionInput('')
      setStudentLastStructuredText('')
    } catch (error) {
      setActionError(`Could not start the lecture: ${error.message}`)
    } finally {
      setBusyAction('')
    }
  }

  async function handleEndLecture() {
    if (!session) return
    speech.stopListening()
    setBusyAction('end')
    setActionError('')
    try {
      const endedSession = await endSession(session.session_id)
      setSession(endedSession)
      setStudentSession(endedSession)
    } catch (error) {
      setActionError(`Could not end the lecture: ${error.message}`)
    } finally {
      setBusyAction('')
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(session.session_id)
      setCopied(true)
    } catch {
      setActionError('Could not copy the ID. Please select and copy it manually.')
    }
  }

  async function handleManualSubmit(e) {
    e.preventDefault()
    const text = manualText.trim()
    if (!text) return
    setManualText('')
    await handleFinalText(text)
  }

  return (
    <main className="shell page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Teacher workspace</p>
          <h1>Start a live lecture</h1>
          <p>Welcome, {user?.name}. Share your session ID, then turn on the microphone and teach normally.</p>
        </div>
        <span className="page-number" aria-hidden="true">01</span>
      </div>

      <section className="control-card" aria-label="Lecture controls">
        <div className="lecture-title-control">
          <label htmlFor="lecture-title" className="field-label">Lecture title</label>
          <input
            id="lecture-title"
            value={lectureTitle}
            onChange={(event) => setLectureTitle(event.target.value)}
            placeholder="For example: Introduction to Python"
            maxLength={200}
            disabled={Boolean(busyAction) || session?.status === 'active'}
          />
        </div>
        <div className="control-row">
          <button
            className="primary-button"
            type="button"
            onClick={handleStartLecture}
            disabled={Boolean(busyAction) || session?.status === 'active'}
          >
            {busyAction === 'start' ? 'Starting…' : 'Start Lecture'}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={handleEndLecture}
            disabled={!session || session.status !== 'active' || Boolean(busyAction)}
          >
            {busyAction === 'end' ? 'Ending…' : 'End Lecture'}
          </button>
          {session?.status === 'active' && (
            <button
              className={`secondary-button microphone-button ${speech.microphoneOn ? 'active' : ''}`}
              type="button"
              onClick={speech.microphoneOn ? speech.stopListening : speech.startListening}
              disabled={speech.isRequesting}
            >
              <span className={speech.microphoneOn ? 'mic-dot active' : 'mic-dot'} aria-hidden="true" />
              {speech.isRequesting
                ? 'Requesting Permission…'
                : speech.microphoneOn
                  ? 'Stop Microphone'
                  : 'Enable Microphone'}
            </button>
          )}
        </div>

        {session && (
          <div className="session-panel">
            <div>
              <span className="field-label">Student session ID</span>
              <strong className="session-id">{session.session_id}</strong>
            </div>
            <button className="copy-button" type="button" onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy ID'}
            </button>
            <span className={`status-badge ${session.status}`}>{session.status}</span>
          </div>
        )}

        {session?.status === 'active' && (
          <div className="microphone-feedback">
            {speech.microphoneOn ? (
              <p className="message microphone-on" role="status">
                <span aria-hidden="true">🎙️</span> Microphone ON
                {speech.isListening ? ' — listening for speech' : ' — starting speech recognition'}
              </p>
            ) : speech.isRequesting ? (
              <p className="message info" role="status">
                <span aria-hidden="true">🎙️</span> Allow microphone access in your browser…
              </p>
            ) : speech.error ? (
              <p className="message error" role="alert">
                <span aria-hidden="true">⚠️</span> {speech.error}
              </p>
            ) : !speech.supported ? (
              <p className="message error" role="alert">
                <span aria-hidden="true">⚠️</span> {speech.supportError || 'Web Speech API not supported.'}
              </p>
            ) : (
              <p className="message info" role="status">
                <span aria-hidden="true">🎙️</span> Microphone is off.
              </p>
            )}
          </div>
        )}

        {session?.status === 'active' && (
          <form className="manual-speech-form" onSubmit={handleManualSubmit}>
            <label htmlFor="manual-speech-input" className="field-label">
              Manual Speech Input (Type or Paste Speech)
            </label>
            <div className="manual-speech-row">
              <input
                id="manual-speech-input"
                type="text"
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                placeholder="Type or paste lecture text (e.g. 'Today we are studying supervised learning...')"
                autoComplete="off"
              />
              <button className="primary-button" type="submit" disabled={!manualText.trim()}>
                Send Speech
              </button>
            </div>
          </form>
        )}
        {actionError && <p className="message error" role="alert">{actionError}</p>}
      </section>

      <TranscriptView
        items={transcript}
        interimText={speech.interimText}
        emptyText="Start the lecture and begin speaking. Your words will appear here."
        sessionId={session?.session_id}
      />
    </main>
  )
}
