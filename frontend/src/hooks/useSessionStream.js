import { useEffect, useState } from 'react'

import { sessionStreamUrl } from '../api/client'

function mergeTranscript(current, incoming) {
  const byId = new Map(current.map((item) => [item.id, item]))
  incoming.forEach((item) => byId.set(item.id, item))
  return [...byId.values()].sort((first, second) => first.id - second.id)
}

// EventSource gives students the saved snapshot, then each new saved result.
// The browser automatically reconnects if the connection briefly drops.
export function useSessionStream(sessionId, externalTranscript, externalSetTranscript) {
  const [internalTranscript, setInternalTranscript] = useState([])
  const transcript = externalTranscript !== undefined ? externalTranscript : internalTranscript
  const setTranscript = externalSetTranscript || setInternalTranscript
  const [connectionState, setConnectionState] = useState('idle')
  const [endedSessionId, setEndedSessionId] = useState('')

  useEffect(() => {
    if (!sessionId) {
      setTranscript([])
      setEndedSessionId('')
      setConnectionState('idle')
      return undefined
    }

    const source = new EventSource(sessionStreamUrl(sessionId))
    setEndedSessionId('')
    setConnectionState('connecting')

    const receiveSnapshot = (event) => {
      const savedItems = JSON.parse(event.data)
      setTranscript(mergeTranscript([], savedItems))
    }

    const receiveTranscript = (event) => {
      const newItem = JSON.parse(event.data)
      setTranscript((current) => mergeTranscript(current, [newItem]))
    }

    const receiveSessionEnded = (event) => {
      const message = JSON.parse(event.data)
      if (message.session_id === sessionId) setEndedSessionId(sessionId)
    }

    source.addEventListener('snapshot', receiveSnapshot)
    source.addEventListener('transcript', receiveTranscript)
    source.addEventListener('session-ended', receiveSessionEnded)
    source.onopen = () => setConnectionState('connected')
    source.onerror = () => setConnectionState('reconnecting')

    return () => {
      source.close()
    }
  }, [sessionId, setTranscript])

  return {
    transcript,
    connectionState,
    sessionEnded: Boolean(sessionId && endedSessionId === sessionId),
  }
}
