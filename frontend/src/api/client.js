// Keep API calls in one small module so pages do not know URL details.
const API_BASE = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'accessible-classroom-token'

async function request(path, options = {}) {
  const { token, ...fetchOptions } = options
  const authToken = token || localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      ...(fetchOptions.body ? { 'Content-Type': 'application/json' } : {}),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...fetchOptions.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(body.detail || `Request failed (${response.status})`)
    error.status = response.status
    throw error
  }

  return response.json()
}

export function register(payload) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function login(payload) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCurrentUser(token) {
  return request('/auth/me', { token })
}

export function joinLectureAttendance(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/attendance/join`, {
    method: 'POST',
  })
}

export function leaveLectureAttendance(sessionId, token) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/attendance/leave`, {
    method: 'POST',
    token,
    keepalive: true,
  })
}

export function getMyLectures() {
  return request('/my-lectures')
}

export function createLecture(title, token) {
  return request('/lectures', {
    method: 'POST',
    body: JSON.stringify({ title }),
    token,
  })
}

export function createSession() {
  return request('/sessions', { method: 'POST' })
}

export function getSession(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}`)
}

export function endSession(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/end`, {
    method: 'POST',
  })
}

export function saveTranscript(sessionId, text) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/transcript`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export function translateTranscript(sessionId, text, targetLanguage) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/translations`, {
    method: 'POST',
    body: JSON.stringify({ text, target_language: targetLanguage }),
  })
}

export function getLectureNotes(sessionId) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/notes`)
}

export function sessionStreamUrl(sessionId) {
  return `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/events`
}

export function structureTranscript(sessionId, text) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/structure`, {
    method: 'POST',
    body: JSON.stringify(text ? { text } : {}),
  })
}

export function askLectureQuestion(sessionId, question, conversationId = null) {
  const payload = { question }
  if (conversationId) {
    payload.conversation_id = conversationId
  }
  return request(`/sessions/${encodeURIComponent(sessionId)}/qa`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getSessionConversation(sessionId, conversationId) {
  return request(
    `/sessions/${encodeURIComponent(sessionId)}/conversations/${encodeURIComponent(conversationId)}`
  )
}


