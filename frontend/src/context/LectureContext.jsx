import { createContext, useContext, useState } from 'react'

const LectureContext = createContext(null)

export function LectureProvider({ children }) {
  // Teacher in-memory state (persists across route switching, clears on browser refresh)
  const [teacherSession, setTeacherSession] = useState(null)
  const [teacherTranscript, setTeacherTranscript] = useState([])

  // Student in-memory state
  const [studentInput, setStudentInput] = useState('')
  const [studentSession, setStudentSession] = useState(null)
  const [studentTranscript, setStudentTranscript] = useState([])
  const [studentStructuredData, setStudentStructuredData] = useState(null)
  const [studentStructureError, setStudentStructureError] = useState('')
  const [studentQaResult, setStudentQaResult] = useState(null)
  const [studentQuestionInput, setStudentQuestionInput] = useState('')
  const [studentLastStructuredText, setStudentLastStructuredText] = useState('')
  const [studentConversationId, setStudentConversationId] = useState(null)
  const [studentConversationMessages, setStudentConversationMessages] = useState([])

  function resetLectureState() {
    setTeacherSession(null)
    setTeacherTranscript([])
    setStudentInput('')
    setStudentSession(null)
    setStudentTranscript([])
    setStudentStructuredData(null)
    setStudentStructureError('')
    setStudentQaResult(null)
    setStudentQuestionInput('')
    setStudentLastStructuredText('')
    setStudentConversationId(null)
    setStudentConversationMessages([])
  }

  return (
    <LectureContext.Provider
      value={{
        teacherSession,
        setTeacherSession,
        teacherTranscript,
        setTeacherTranscript,
        studentInput,
        setStudentInput,
        studentSession,
        setStudentSession,
        studentTranscript,
        setStudentTranscript,
        studentStructuredData,
        setStudentStructuredData,
        studentStructureError,
        setStudentStructureError,
        studentQaResult,
        setStudentQaResult,
        studentQuestionInput,
        setStudentQuestionInput,
        studentLastStructuredText,
        setStudentLastStructuredText,
        studentConversationId,
        setStudentConversationId,
        studentConversationMessages,
        setStudentConversationMessages,
        resetLectureState,
      }}
    >
      {children}
    </LectureContext.Provider>
  )
}

export function useLectureContext() {
  const context = useContext(LectureContext)
  if (!context) {
    throw new Error('useLectureContext must be used within a LectureProvider')
  }
  return context
}
