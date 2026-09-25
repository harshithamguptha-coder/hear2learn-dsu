import StatusBadge from './StatusBadge'
import TranscriptView from './TranscriptView'

export default function TeacherLectureStudio({
  session,
  lectureTitle,
  onLectureTitleChange,
  lectureSubject,
  onLectureSubjectChange,
  onStart,
  onEnd,
  onCopy,
  copied,
  busyAction,
  actionError,
  speech,
  transcript,
  interimText,
  manualText,
  onManualTextChange,
  onManualSubmit,
  onBackToOverview,
  onStartAnotherLecture,
}) {
  const active = session?.status === 'active'
  const captions = session ? (
    <TranscriptView
      id="teacher-captions"
      className="teacher-live-captions"
      items={transcript}
      interimText={active ? interimText : ''}
      emptyText={active ? 'Start speaking or use manual speech input. Your captions will appear here and stream to students.' : 'No speech segments were saved for this lecture.'}
      isLive={active}
    />
  ) : null

  return (
    <div className="view-stack lecture-studio-view">
      <section className="page-intro">
        <div><p className="eyebrow">Live classroom control</p><h1>{active ? 'Your lecture is live' : 'Start a new lecture'}</h1><p>{active ? 'Share the session ID, enable your microphone, and teach with a live transcript.' : 'Create a real classroom session. Students can join with the unique session ID.'}</p></div>
        {session && <StatusBadge status={session.status} />}
      </section>

      <section className="studio-card" aria-labelledby="lecture-studio-title">
        <div className="studio-card-heading"><span className="studio-icon" aria-hidden="true">✦</span><div><p className="eyebrow">Teacher controls</p><h2 id="lecture-studio-title">{active ? 'Live lecture' : 'Start a new class'}</h2></div></div>
        {!session ? (
          <form className="start-lecture-form" onSubmit={(event) => { event.preventDefault(); onStart() }}>
            <label htmlFor="lecture-title">Lecture title</label>
            <input id="lecture-title" value={lectureTitle} onChange={(event) => onLectureTitleChange(event.target.value)} placeholder="For example: Introduction to Python" maxLength={160} required />
            <label htmlFor="lecture-subject">Subject or topic <span className="optional-label">Optional</span></label>
            <input id="lecture-subject" value={lectureSubject} onChange={(event) => onLectureSubjectChange(event.target.value)} placeholder="For example: Computer science" maxLength={60} />
            <p className="field-help">Your title and optional topic are stored together in the lecture record.</p>
            <button className="primary-button" type="submit" disabled={Boolean(busyAction)}>{busyAction === 'start' ? 'Starting lecture…' : 'Start lecture'}</button>
          </form>
        ) : active ? (
          <>
            <div className="live-session-banner"><div><span className="live-pulse" aria-hidden="true" /><span><small>Live session</small><strong>{session.title}</strong></span></div><StatusBadge status="active" /></div>
            <div className="studio-actions"><button className="primary-button microphone-button" type="button" onClick={speech.microphoneOn ? speech.stopListening : speech.startListening} disabled={speech.isRequesting}><span className={speech.microphoneOn ? 'mic-dot active' : 'mic-dot'} aria-hidden="true" />{speech.isRequesting ? 'Requesting permission…' : speech.microphoneOn ? 'Stop microphone' : 'Enable microphone'}</button><button className="danger-button" type="button" onClick={onEnd} disabled={Boolean(busyAction)}>{busyAction === 'end' ? 'Ending lecture…' : 'End lecture'}</button></div>
            <div className="microphone-feedback">{speech.isReconnecting ? <p className="message info speech-reconnecting" role="status"><span className="reconnecting-spinner" aria-hidden="true" /> Reconnecting microphone… The lecture is still live.</p> : speech.microphoneOn ? <p className="message microphone-on" role="status"><span aria-hidden="true">🎙</span> Microphone on — {speech.isListening ? 'listening for speech' : 'starting speech recognition'}</p> : speech.isRequesting ? <p className="message info" role="status">Allow microphone access in your browser…</p> : speech.error ? <p className="message speech-warning" role="status">{speech.error}</p> : !speech.supported ? <p className="message speech-warning" role="status">{speech.supportError || 'Speech recognition is not supported in this browser.'}</p> : <p className="message info" role="status">Microphone is off. Enable it when you are ready to speak.</p>}</div>
            {captions}
            <div className="session-share-card"><div><span className="field-label">Student session ID</span><strong className="session-id-large">{session.session_id}</strong><p>Students receive the same saved captions in real time.</p></div><button className="secondary-button" type="button" onClick={onCopy}>{copied ? 'Copied!' : 'Copy session ID'}</button></div>
            <form className="manual-speech-form" onSubmit={onManualSubmit}><label htmlFor="manual-speech-input">Manual speech input</label><div className="manual-speech-row"><input id="manual-speech-input" value={manualText} onChange={(event) => onManualTextChange(event.target.value)} placeholder="Type or paste lecture text" autoComplete="off" /><button className="primary-button" type="submit" disabled={!manualText.trim()}>Send speech</button></div><p className="field-help">Useful for testing the classroom when speech recognition is unavailable.</p></form>
          </>
        ) : (
          <div className="ended-lecture-view">
            <div className="ended-session-banner"><div><StatusBadge status="ended" /><span><small>Saved lecture</small><strong>{session.title}</strong></span></div><code>{session.session_id}</code></div>
            {captions}
            <div className="ended-lecture-actions"><button className="secondary-button" type="button" onClick={onBackToOverview}>← Back to teacher overview</button><button className="primary-button" type="button" onClick={onStartAnotherLecture}>Start another lecture</button></div>
          </div>
        )}
        {actionError && <p className="message error" role="alert">{actionError}</p>}
      </section>
      {session && <section className="teacher-session-summary" aria-label="Current lecture"><p><strong>{session.status === 'active' ? 'Live transcript is on.' : 'This lecture has ended.'}</strong> Students receive the saved transcript and the session status from the classroom API.</p></section>}
    </div>
  )
}
