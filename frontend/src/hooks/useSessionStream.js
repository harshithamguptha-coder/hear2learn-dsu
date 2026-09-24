import { useEffect, useState } from 'react'

import { sessionStreamUrl } from '../api/client'

function mergeTranscript(current, incoming) {
  const byId = new Map(current.map((item) => [item.id, item]))
  incoming.forEach((item) => byId.set(item.id, item))
  return [...byId.values()].sort((first, second) => first.id - second.id)
}

// EventSource gives students the saved snapshot, then each new saved result.
// The browser automatically reconnects if the connection briefly drops.
export function useSessionStream(sessionId) {
  const [transcript, setTranscript] = useState([])
  const [connectionState, setConnectionState] = useState('idle')

  useEffect(() => {
    if (!sessionId) {
      setTranscript([])
      setConnectionState('idle')
      return undefined
    }

    const source = new EventSource(sessionStreamUrl(sessionId))
    setTranscript([])
    setConnectionState('connecting')

    const receiveSnapshot = (event) => {
      const savedItems = JSON.parse(event.data)
      setTranscript(mergeTranscript([], savedItems))
    }

    const receiveTranscript = (event) => {
      const newItem = JSON.parse(event.data)
      setTranscript((current) => mergeTranscript(current, [newItem]))
    }

    source.addEventListener('snapshot', receiveSnapshot)
    source.addEventListener('transcript', receiveTranscript)
    source.onopen = () => setConnectionState('connected')
    source.onerror = () => setConnectionState('reconnecting')

    return () => {
      source.close()
    }
  }, [sessionId])

  return { transcript, connectionState }
}
