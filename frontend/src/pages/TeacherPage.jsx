import { useCallback, useState } from 'react'

import { createSession, endSession, saveTranscript } from '../api/client'
import TranscriptView from '../components/TranscriptView'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

function mergeItem(current, newItem) {
  return current.some((item) => item.id === newItem.id)
    ? current
    : [...current, newItem]
}

export default function TeacherPage() {
  const [session, setSession] = useState(null)
  const [transcript, setTranscript] = useState([])
  const [actionError, setActionError] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [copied, setCopied] = useState(false)

  const handleFinalText = useCallback(async (text) => {
    if (!session || session.status !== 'active') return

    try {
      const savedItem = await saveTranscript(session.session_id, text)
      setTranscript((current) => mergeItem(current, savedItem))
    } catch (error) {
      setActionError(`Could not save transcript: ${error.message}`)
    }
  }, [session])

  const speech = useSpeechRecognition(handleFinalText)

  async function handleStartLecture() {
    setBusyAction('start')
    setActionError('')
    setCopied(false)
    try {
      const newSession = await createSession()
      setSession(newSession)
      setTranscript([])
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

  return (
    <main className="shell page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Teacher workspace</p>
          <h1>Start a live lecture</h1>
          <p>Share your session ID, then turn on the microphone and teach normally.</p>
        </div>
        <span className="page-number" aria-hidden="true">01</span>
      </div>

      <section className="control-card" aria-label="Lecture controls">
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
              className="secondary-button microphone-button"
              type="button"
              onClick={speech.listening ? speech.stopListening : speech.startListening}
              disabled={!speech.supported}
            >
              <span className={speech.listening ? 'mic-dot active' : 'mic-dot'} aria-hidden="true" />
              {speech.listening ? 'Stop Microphone' : 'Start Microphone'}
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

        {!speech.supported && session?.status === 'active' && (
          <p className="message error" role="alert">
            This browser does not support Web Speech recognition. Use the latest
            Chrome or Edge over HTTPS or localhost.
          </p>
        )}
        {speech.error && <p className="message error" role="alert">{speech.error}</p>}
        {actionError && <p className="message error" role="alert">{actionError}</p>}
      </section>

      <TranscriptView
        items={transcript}
        interimText={speech.interimText}
        emptyText="Start the lecture and begin speaking. Your words will appear here."
      />
    </main>
  )
}
