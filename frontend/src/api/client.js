// Keep API calls in one small module so pages do not know URL details.
const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
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

export function sessionStreamUrl(sessionId) {
  return `${API_BASE}/sessions/${encodeURIComponent(sessionId)}/events`
}

export function structureTranscript(sessionId, text) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/structure`, {
    method: 'POST',
    body: JSON.stringify(text ? { text } : {}),
  })
}

export function askLectureQuestion(sessionId, question) {
  return request(`/sessions/${encodeURIComponent(sessionId)}/qa`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}

