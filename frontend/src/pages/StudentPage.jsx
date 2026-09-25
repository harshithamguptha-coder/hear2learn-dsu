import { useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { useEffect, useRef, useState } from 'react'

import {
  getAccessibilityPreference,
  getLectureNotes,
  getMyLectures,
  getSession,
  joinLectureAttendance,
  leaveLectureAttendance,
  saveAccessibilityPreference,
  structureTranscript,
} from '../api/client'
import AppShell from '../components/AppShell'
import SettingsView from '../components/SettingsView'
import StudentJoin from '../components/StudentJoin'
import StudentLectureList from '../components/StudentLectureList'
import StudentLiveWorkspace from '../components/StudentLiveWorkspace'
import StudentOverview from '../components/StudentOverview'
import { useLectureContext } from '../context/LectureContext'
import { useSessionStream } from '../hooks/useSessionStream'
import { getAiFeatureError, isAiUnavailableError } from '../services/aiErrors'

export default function StudentPage() {
  const { user, token, logout } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get('view') || 'overview'
  const activeView = ['overview', 'lectures', 'join', 'live', 'settings'].includes(view) ? view : 'overview'
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
    studentConversationId: conversationId,
    setStudentConversationId: setConversationId,
    studentConversationMessages: conversationMessages,
    setStudentConversationMessages: setConversationMessages,
    studentLastStructuredText,
    setStudentLastStructuredText,
    teacherSession,
    resetLectureState,
  } = useLectureContext()

  const [error, setError] = useState('')
  const [joining, setJoining] = useState(false)
  const [structuring, setStructuring] = useState(false)
  const [accessibilityMode, setAccessibilityMode] = useState('standard')
  const [translationLanguage, setTranslationLanguage] = useState('kn')
  const [preferenceAvailable, setPreferenceAvailable] = useState(false)
  const [preferenceLoading, setPreferenceLoading] = useState(false)
  const [preferenceSaving, setPreferenceSaving] = useState(false)
  const [preferenceError, setPreferenceError] = useState('')
  const [notes, setNotes] = useState(null)
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesError, setNotesError] = useState('')
  const [myLectures, setMyLectures] = useState([])
  const [myLecturesLoading, setMyLecturesLoading] = useState(true)
  const [myLecturesError, setMyLecturesError] = useState('')
  const [leaving, setLeaving] = useState(false)

  const { transcript, connectionState, sessionEnded } = useSessionStream(
    session?.session_id,
    studentTranscript,
    setStudentTranscript,
  )
  const lastStructuredTextRef = useRef(studentLastStructuredText)
  const activeAttendanceSessionRef = useRef('')
  const preferenceRequestRef = useRef(0)
  const aiUnavailableSessionRef = useRef('')

  function resetAccessibilityPreference() {
    preferenceRequestRef.current += 1
    setAccessibilityMode('standard')
    setTranslationLanguage('kn')
    setPreferenceAvailable(false)
    setPreferenceLoading(false)
    setPreferenceSaving(false)
    setPreferenceError('')
  }

  async function refreshMyLectures() {
    setMyLecturesLoading(true)
    setMyLecturesError('')
    try {
      setMyLectures(await getMyLectures())
    } catch (requestError) {
      setMyLecturesError(`Could not load your lecture history: ${requestError.message}`)
    } finally {
      setMyLecturesLoading(false)
    }
  }

  useEffect(() => {
    refreshMyLectures()
  }, [])

  function changeView(nextView) {
    setSearchParams({ view: nextView })
  }

  function handleLogout() {
    resetLectureState()
    logout()
    navigate('/', { replace: true })
  }

  async function recordAttendance(sessionId) {
    if (!user || user.role !== 'student' || activeAttendanceSessionRef.current === sessionId) {
      return activeAttendanceSessionRef.current === sessionId
    }
    try {
      await joinLectureAttendance(sessionId, token)
      activeAttendanceSessionRef.current = sessionId
      await refreshMyLectures()
      return true
    } catch (attendanceError) {
      setError(`Could not record lecture attendance: ${attendanceError.message}`)
      return false
    }
  }

  useEffect(() => {
    const sessionId = session?.session_id
    const requestId = ++preferenceRequestRef.current
    if (!sessionId) {
      resetAccessibilityPreference()
      return undefined
    }

    let cancelled = false
    setPreferenceLoading(true)
    setPreferenceAvailable(false)
    setPreferenceError('')
    getAccessibilityPreference(sessionId, token)
      .then((savedPreference) => {
        if (cancelled || requestId !== preferenceRequestRef.current) return
        setAccessibilityMode(savedPreference.mode)
        setTranslationLanguage(savedPreference.translation_language)
        setPreferenceAvailable(true)
      })
      .catch((requestError) => {
        if (cancelled || requestId !== preferenceRequestRef.current) return
        setPreferenceAvailable(false)
        setPreferenceError(
          `Your saved mode could not be loaded: ${requestError.message}`,
        )
      })
      .finally(() => {
        if (cancelled || requestId !== preferenceRequestRef.current) return
        setPreferenceLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [session?.session_id, token])

  async function persistAccessibility(nextMode, nextLanguage = translationLanguage) {
    const sessionId = session?.session_id
    if (!sessionId || !preferenceAvailable || preferenceSaving) return

    const previousMode = accessibilityMode
    const previousLanguage = translationLanguage
    const requestId = ++preferenceRequestRef.current
    setAccessibilityMode(nextMode)
    setTranslationLanguage(nextLanguage)
    setPreferenceSaving(true)
    setPreferenceError('')

    try {
      const savedPreference = await saveAccessibilityPreference(
        sessionId,
        nextMode,
        nextLanguage,
        token,
      )
      if (requestId !== preferenceRequestRef.current) return
      setAccessibilityMode(savedPreference.mode)
      setTranslationLanguage(savedPreference.translation_language)
    } catch (requestError) {
      if (requestId !== preferenceRequestRef.current) return
      setAccessibilityMode(previousMode)
      setTranslationLanguage(previousLanguage)
      setPreferenceError(
        `Your mode was not saved. The previous setting is still active: ${requestError.message}`,
      )
    } finally {
      if (requestId === preferenceRequestRef.current) setPreferenceSaving(false)
    }
  }

  function handleViewLecture(lecture) {
    const sessionId = lecture?.session_id
    if (!sessionId) return
    setInput(sessionId)
    setStudentTranscript([])
    setStructuredData(null)
    setStructureError('')
    setQaResult(null)
    setStudentLastStructuredText('')
    lastStructuredTextRef.current = ''
    setNotes(null)
    setNotesError('')
    resetAccessibilityPreference()
    setJoining(true)
    setError('')
    getSession(sessionId)
      .then((foundSession) => {
        if (foundSession.status === 'active' && activeAttendanceSessionRef.current !== sessionId) {
          return recordAttendance(sessionId).then((saved) => {
            if (saved) {
              setSession(foundSession)
              changeView('live')
            }
            return saved
          })
        }
        setSession(foundSession)
        changeView('live')
        return true
      })
      .catch((requestError) => setError(`Could not open this lecture: ${requestError.message}`))
      .finally(() => setJoining(false))
  }

  async function handleLeaveLecture() {
    if (!session || leaving) return
    setLeaving(true)
    setError('')
    try {
      await leaveLectureAttendance(session.session_id, token)
      activeAttendanceSessionRef.current = ''
      setSession(null)
      setStudentTranscript([])
      setStructuredData(null)
      setStructureError('')
      setQaResult(null)
      setNotes(null)
      setNotesError('')
      setStudentLastStructuredText('')
      lastStructuredTextRef.current = ''
      resetAccessibilityPreference()
      await refreshMyLectures()
      changeView('overview')
    } catch (leaveError) {
      setError(`Could not leave the lecture: ${leaveError.message}`)
    } finally {
      setLeaving(false)
    }
  }

  useEffect(() => () => {
    const sessionId = activeAttendanceSessionRef.current
    if (sessionId) leaveLectureAttendance(sessionId, token).catch(() => {})
  }, [token])

  // If student is not connected and teacher has an active session, auto-connect for seamless switching
  useEffect(() => {
    if (session || !teacherSession?.session_id) return undefined
    let cancelled = false
    setInput(teacherSession.session_id)
    recordAttendance(teacherSession.session_id).then((attendanceSaved) => {
      if (!cancelled && attendanceSaved) {
        setSession(teacherSession)
        setSearchParams({ view: 'live' })
      }
    })
    return () => {
      cancelled = true
    }
  }, [session, teacherSession, setInput, setSession])

  useEffect(() => {
    if (sessionEnded) {
      if (activeAttendanceSessionRef.current === session?.session_id) {
        leaveLectureAttendance(session.session_id, token).catch(() => {})
        activeAttendanceSessionRef.current = ''
      }
      setSession((current) => (
        current ? { ...current, status: 'ended' } : current
      ))
      refreshMyLectures()
    }
  }, [sessionEnded, session?.session_id, setSession, token])

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

    const previousAttendanceSession = activeAttendanceSessionRef.current
    if (previousAttendanceSession && previousAttendanceSession !== sessionId) {
      try {
        await leaveLectureAttendance(previousAttendanceSession, token)
      } catch {
        // The new lecture can still be opened if the old leave request fails.
      }
      activeAttendanceSessionRef.current = ''
    }

    setSession(null)
    setStudentTranscript([])
    setStructuredData(null)
    setStructureError('')
    setQaResult(null)
    setStudentLastStructuredText('')
    lastStructuredTextRef.current = ''
    setNotes(null)
    setNotesError('')
    resetAccessibilityPreference()

    try {
      const foundSession = await getSession(sessionId)
      if (foundSession.status === 'active') {
        const attendanceSaved = await recordAttendance(sessionId)
        if (!attendanceSaved) return
      }
      setSession(foundSession)
      changeView('live')
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
    const sessionId = session?.session_id
    if (!sessionId) return
    if (aiUnavailableSessionRef.current === sessionId) return

    const fullText = transcript.map((item) => item.text).join(' ').trim()
    if (!fullText) return

    if (structuredData && (fullText === lastStructuredTextRef.current || fullText === studentLastStructuredText)) return

    const delay = structuredData ? 1500 : 250
    let cancelled = false
    const timer = setTimeout(async () => {
      setStructuring(true)
      try {
        const result = await structureTranscript(sessionId, fullText)
        if (cancelled) return
        aiUnavailableSessionRef.current = ''
        setStructuredData(result)
        lastStructuredTextRef.current = fullText
        setStudentLastStructuredText(fullText)
        setStructureError('')
      } catch (error) {
        if (cancelled) return
        if (isAiUnavailableError(error)) aiUnavailableSessionRef.current = sessionId
        setStructureError(getAiFeatureError(error, 'AI lesson insights'))
      } finally {
        if (!cancelled) setStructuring(false)
      }
    }, delay)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
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
  let content
  if (activeView === 'join') {
    content = <StudentJoin input={input} onInputChange={(event) => setInput(event.target.value)} onSubmit={handleJoin} joining={joining} error={error} />
  } else if (activeView === 'lectures') {
    content = <StudentLectureList lectures={myLectures} loading={myLecturesLoading} error={myLecturesError} onViewLecture={handleViewLecture} />
  } else if (activeView === 'settings') {
    content = <SettingsView user={user} role="student" onLogout={handleLogout} />
  } else if (activeView === 'live' && session) {
    content = <StudentLiveWorkspace user={user} session={session} transcript={transcript} connectionLabel={connectionLabel} accessibilityMode={accessibilityMode} onModeChange={persistAccessibility} translationLanguage={translationLanguage} onTranslationLanguageChange={(language) => persistAccessibility('translation', language)} preferenceAvailable={preferenceAvailable} preferenceLoading={preferenceLoading} preferenceSaving={preferenceSaving} preferenceError={preferenceError} onLeave={handleLeaveLecture} leaving={leaving} structuredData={structuredData} structuring={structuring} structureError={structureError} notes={notes} notesLoading={notesLoading} notesError={notesError} qaResult={qaResult} setQaResult={setQaResult} questionInput={questionInput} setQuestionInput={setQuestionInput} conversationId={conversationId} setConversationId={setConversationId} conversationMessages={conversationMessages} setConversationMessages={setConversationMessages} />
  } else {
    content = <StudentOverview user={user} lectures={myLectures} loading={myLecturesLoading} error={myLecturesError} session={session} onViewChange={changeView} onViewLecture={handleViewLecture} />
  }

  return (
    <AppShell user={user} role="student" activeView={activeView} liveLecture={session?.status === 'active' ? session : null} onLogout={handleLogout}>
      {content}
    </AppShell>
  )
}
