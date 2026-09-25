import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { createLecture, endSession, getTeacherDashboard, getTranscript, saveTranscript } from '../api/client'
import AppShell from '../components/AppShell'
import SettingsView from '../components/SettingsView'
import TeacherAnalytics from '../components/TeacherAnalytics'
import TeacherLectureDetail from '../components/TeacherLectureDetail'
import TeacherLectureList from '../components/TeacherLectureList'
import TeacherLectureStudio from '../components/TeacherLectureStudio'
import TeacherOverview from '../components/TeacherOverview'
import { useAuth } from '../context/AuthContext'
import { useLectureContext } from '../context/LectureContext'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

function mergeTranscript(current, incoming) {
  const byId = new Map(current.map((item) => [item.id, item]))
  incoming.forEach((item) => byId.set(item.id, item))
  return [...byId.values()].sort((first, second) => first.id - second.id)
}

function mergeItem(current, newItem) {
  return mergeTranscript(current, [newItem])
}

export default function TeacherPage() {
  const { user, token, logout } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get('view') || 'overview'
  const selectedSessionId = searchParams.get('session') || ''
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
    resetLectureState,
  } = useLectureContext()

  const [actionError, setActionError] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [copied, setCopied] = useState(false)
  const [manualText, setManualText] = useState('')
  const [lectureTitle, setLectureTitle] = useState('Untitled Lecture')
  const [lectureSubject, setLectureSubject] = useState('')
  const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0)
  const [activeLecture, setActiveLecture] = useState(null)

  useEffect(() => {
    let cancelled = false
    getTeacherDashboard(token)
      .then((dashboard) => {
        if (cancelled) return
        const liveLecture = dashboard.lectures?.find((lecture) => lecture.status === 'active') || null
        setActiveLecture(liveLecture)
        setSession((current) => {
          if (liveLecture) return current?.status === 'active' ? current : liveLecture
          return current?.status === 'active' ? null : current
        })
      })
      .catch(() => {
        if (!cancelled) setActiveLecture(null)
      })
    return () => { cancelled = true }
  }, [token, dashboardRefreshKey])

  useEffect(() => {
    const sessionId = session?.session_id
    if (!sessionId) {
      setTranscript([])
      return undefined
    }
    let cancelled = false
    setTranscript([])
    getTranscript(sessionId, token)
      .then((savedItems) => {
        if (!cancelled) setTranscript((current) => mergeTranscript(current, savedItems))
      })
      .catch(() => {
        // Existing in-memory captions remain available if this refresh fails.
      })
    return () => { cancelled = true }
  }, [session?.session_id, token, setTranscript])

  const sessionRef = useRef(session)
  useEffect(() => {
    sessionRef.current = session
  }, [session])

  const handleFinalText = useCallback(async (text) => {
    const currentSession = sessionRef.current

    if (!currentSession || currentSession.status !== 'active') return

    const sessionId = currentSession.session_id

    try {
      const savedItem = await saveTranscript(sessionId, text)
      if (sessionRef.current?.session_id !== sessionId) return
      setTranscript((current) => mergeItem(current, savedItem))
      setActionError('')
    } catch (error) {
      setActionError(`Could not save transcript: ${error.message}`)
    }
  }, [setTranscript])

  const speech = useSpeechRecognition(handleFinalText)

  function changeView(nextView) {
    setSearchParams({ view: nextView })
  }

  async function handleLogout() {
    speech.stopListening()
    const lectureToEnd = activeLecture || session
    if (lectureToEnd?.status === 'active') {
      try {
        const endedSession = await endSession(lectureToEnd.session_id)
        setSession(endedSession)
        setActiveLecture(null)
      } catch {
        setActionError('The lecture could not be ended before logout. Please try again.')
        return
      }
    }
    resetLectureState()
    setActiveLecture(null)
    logout()
    navigate('/', { replace: true })
  }

  function handleViewLecture(lecture) {
    if (!lecture?.session_id) return
    setSearchParams({ view: 'lecture', session: lecture.session_id })
  }

  async function handleStartLecture() {
    setBusyAction('start')
    setActionError('')
    setCopied(false)
    try {
      const fullTitle = [lectureTitle.trim() || 'Untitled Lecture', lectureSubject.trim()]
        .filter(Boolean)
        .join(' — ')
        .slice(0, 200)
      const newSession = await createLecture(fullTitle, token)
      setSession(newSession)
      setActiveLecture(newSession)
      setTranscript([])
      setStudentSession(newSession)
      setStudentInput(newSession.session_id)
      setStudentTranscript([])
      setStudentStructuredData(null)
      setStudentStructureError('')
      setStudentQaResult(null)
      setStudentQuestionInput('')
      setStudentLastStructuredText('')
      setDashboardRefreshKey((value) => value + 1)
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
      setActiveLecture(null)
      setStudentSession(endedSession)
      setDashboardRefreshKey((value) => value + 1)
    } catch (error) {
      setActionError(`Could not end the lecture: ${error.message}`)
    } finally {
      setBusyAction('')
    }
  }

  function handleStartAnotherLecture() {
    setSession(null)
    setTranscript([])
    setActionError('')
    setCopied(false)
    setManualText('')
    setLectureTitle('Untitled Lecture')
    setLectureSubject('')
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

  const activeView = ['overview', 'lectures', 'lecture', 'new', 'analytics', 'settings'].includes(view) ? view : 'overview'
  let content
  if (activeView === 'lectures') {
    content = <TeacherLectureList token={token} refreshKey={dashboardRefreshKey} onViewLecture={handleViewLecture} />
  } else if (activeView === 'lecture' && selectedSessionId) {
    content = <TeacherLectureDetail sessionId={selectedSessionId} token={token} onBack={() => changeView('lectures')} />
  } else if (activeView === 'new') {
    content = <TeacherLectureStudio session={session} lectureTitle={lectureTitle} onLectureTitleChange={setLectureTitle} lectureSubject={lectureSubject} onLectureSubjectChange={setLectureSubject} onStart={handleStartLecture} onEnd={handleEndLecture} onCopy={handleCopy} copied={copied} busyAction={busyAction} actionError={actionError} speech={speech} transcript={transcript} interimText={speech.interimText} manualText={manualText} onManualTextChange={setManualText} onManualSubmit={handleManualSubmit} onBackToOverview={() => changeView('overview')} onStartAnotherLecture={handleStartAnotherLecture} />
  } else if (activeView === 'analytics') {
    content = <TeacherAnalytics token={token} refreshKey={dashboardRefreshKey} />
  } else if (activeView === 'settings') {
    content = <SettingsView user={user} role="teacher" onLogout={handleLogout} />
  } else {
    content = <TeacherOverview token={token} refreshKey={dashboardRefreshKey} onViewChange={changeView} onViewLecture={handleViewLecture} />
  }

  return (
    <AppShell user={user} role="teacher" activeView={activeView === 'lecture' ? 'lectures' : activeView} liveLecture={activeLecture} onLogout={handleLogout}>
      {content}
    </AppShell>
  )
}
