import { useEffect, useState } from 'react'

import { getLectureNotes, getSession, getTeacherDashboard, getTranscript } from '../api/client'
import EmptyState from './EmptyState'
import StatusBadge from './StatusBadge'

const MODES = [
  ['standard', 'Standard', 'Aa'],
  ['simplified', 'Simplified', '✦'],
  ['translation', 'Translation', '文'],
  ['sign_support', 'Sign Support', '🤟'],
]

function formatDate(value) {
  if (!value) return 'No data'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatTime(value) {
  if (!value) return 'No data'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function formatDuration(seconds) {
  const minutes = Math.max(0, Math.floor(Number(seconds || 0) / 60))
  const hours = Math.floor(minutes / 60)
  return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`
}

export default function TeacherLectureDetail({ sessionId, token, onBack }) {
  const [data, setData] = useState({ session: null, analytics: null, transcript: [], notes: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!sessionId) return undefined
    let cancelled = false
    setLoading(true)
    setError('')
    (async () => {
      try {
        const dashboard = await getTeacherDashboard(token)
        const selectedAnalytics = dashboard.lectures?.find((lecture) => lecture.session_id === sessionId) || null
        if (!selectedAnalytics) throw new Error('This lecture is not in the logged-in teacher’s stored lectures.')
        const [session, transcript, notes] = await Promise.all([
          getSession(sessionId, token),
          getTranscript(sessionId, token),
          getLectureNotes(sessionId, token).catch((requestError) => requestError.status === 409 ? null : Promise.reject(requestError)),
        ])
        if (cancelled) return
        setData({ session, analytics: selectedAnalytics, transcript, notes })
      } catch (requestError) {
        if (!cancelled) setError(`This lecture could not be loaded: ${requestError.message}`)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [sessionId, token])

  const { session, analytics, transcript, notes } = data
  if (loading) return <div className="loading-card" role="status">Loading this lecture only…</div>
  if (error) return <div className="view-stack"><p className="message error" role="alert">{error}</p><button className="secondary-button" type="button" onClick={onBack}>← Back to Recent Lectures</button></div>
  if (!session) return <EmptyState icon="▤" title="Lecture not found" description="This stored lecture is no longer available." action={<button className="secondary-button" type="button" onClick={onBack}>← Back to Recent Lectures</button>} />

  return (
    <div className="view-stack lecture-detail-view">
      <section className="page-intro"><div><button className="back-button" type="button" onClick={onBack}>← Back to Recent Lectures</button><p className="eyebrow">Selected lecture · {session.session_id}</p><h1>{session.title || analytics?.title || 'Untitled Lecture'}</h1><p>Only the stored records for this session are shown below.</p></div><StatusBadge status={session.status} /></section>
      <section className="lecture-detail-card"><div className="analytics-facts"><div><span>Date</span><strong>{formatDate(analytics?.lecture_date || session.start_time || session.started_at)}</strong></div><div><span>Start time</span><strong>{formatTime(analytics?.start_time || session.start_time)}</strong></div><div><span>End time</span><strong>{formatTime(analytics?.end_time || session.end_time)}</strong></div><div><span>Duration</span><strong>{formatDuration(analytics?.duration_seconds)}</strong></div><div><span>Students attended</span><strong>{analytics?.students_attended ?? 0}</strong></div><div><span>Questions asked</span><strong>{analytics?.questions_asked ?? 0}</strong></div></div><div className="analytics-detail-grid"><section><h3>Detected topics</h3>{analytics?.detected_topics?.length ? <div className="topic-tags">{analytics.detected_topics.map((topic) => <span key={topic}>{topic}</span>)}</div> : <p className="muted-copy">No topics stored yet.</p>}</section><section><h3>Accessibility usage</h3><div className="usage-grid">{MODES.map(([key, label, icon]) => <div key={key}><span aria-hidden="true">{icon}</span><span>{label}</span><strong>{analytics?.accessibility_usage?.[key] ?? 0}</strong></div>)}</div></section></div></section>
      <section className="workspace-section" aria-labelledby="selected-transcript-title"><div className="section-heading-row"><div><p className="eyebrow">Saved session transcript</p><h2 id="selected-transcript-title">Lecture transcript</h2></div><span>{transcript.length} {transcript.length === 1 ? 'segment' : 'segments'}</span></div>{transcript.length ? <ol className="detail-transcript-list">{transcript.map((item) => <li key={item.id}><time dateTime={item.created_at}>{formatTime(item.created_at)}</time><p>{item.text}</p></li>)}</ol> : <EmptyState icon="Aa" title="No saved transcript" description="No transcript segments are stored for this session." />}</section>
      <section className="workspace-section" aria-labelledby="selected-notes-title"><div className="section-heading-row"><div><p className="eyebrow">Session-scoped notes</p><h2 id="selected-notes-title">Lecture notes</h2></div></div>{notes ? <div className="detail-notes"><p>{notes.summary}</p><div className="topic-tags">{(notes.main_topics || []).map((topic) => <span key={topic}>{topic}</span>)}</div></div> : <EmptyState icon="▤" title="Notes are not available" description={session.status === 'active' ? 'Notes are generated when this lecture ends.' : 'No notes were generated for this session.'} />}</section>
    </div>
  )
}
