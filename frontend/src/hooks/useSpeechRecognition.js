import { useCallback, useEffect, useRef, useState } from 'react'

const ERROR_MESSAGES = {
  'audio-capture': 'No microphone was found. Check your system sound input settings.',
  'not-allowed': 'Microphone access was blocked. Click the lock icon in the address bar to allow microphone access.',
  'network': 'Speech recognition service network error. If using Edge/Chrome, check your internet.',
  'service-not-allowed': 'This browser could not start speech recognition service.',
  'language-not-supported': 'This browser does not support en-US speech recognition.',
}

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export function useSpeechRecognition(onFinalText) {
  const recognitionRef = useRef(null)
  const callbackRef = useRef(onFinalText)
  const shouldListenRef = useRef(false)
  const restartTimerRef = useRef(null)
  const [listening, setListening] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [error, setError] = useState('')
  const supported = Boolean(getSpeechRecognition())

  useEffect(() => {
    callbackRef.current = onFinalText
  }, [onFinalText])

  const createAndStart = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) return

    // Clean up any lingering previous instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onstart = null
        recognitionRef.current.onresult = null
        recognitionRef.current.onerror = null
        recognitionRef.current.onend = null
        recognitionRef.current.abort()
      } catch {
        // ignore
      }
      recognitionRef.current = null
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setError('')
      setListening(true)
    }

    recognition.onresult = (event) => {
      let interim = ''
      let final = ''

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        if (result.isFinal) {
          final += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }

      setInterimText(interim.trim())
      if (final.trim()) {
        callbackRef.current(final.trim())
      }
    }

    recognition.onerror = (event) => {
      // 'no-speech' happens naturally when the speaker pauses; do not show error or stop
      if (event.error === 'no-speech') {
        return
      }

      if (event.error !== 'aborted') {
        setError(
          ERROR_MESSAGES[event.error] ||
            `Speech recognition error: ${event.error}`,
        )
      }

      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        shouldListenRef.current = false
      }
      setListening(false)
    }

    recognition.onend = () => {
      setListening(false)
      setInterimText('')

      if (shouldListenRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (!shouldListenRef.current) return
          createAndStart()
        }, 150)
      }
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch (err) {
      setError(`Could not start microphone: ${err.message}`)
      shouldListenRef.current = false
      setListening(false)
    }
  }, [])

  const startListening = useCallback(() => {
    if (!supported) return
    setError('')
    shouldListenRef.current = true
    createAndStart()
  }, [supported, createAndStart])

  const stopListening = useCallback(() => {
    shouldListenRef.current = false
    window.clearTimeout(restartTimerRef.current)
    setInterimText('')
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore
      }
    }
    setListening(false)
  }, [])

  useEffect(() => {
    return () => {
      shouldListenRef.current = false
      window.clearTimeout(restartTimerRef.current)
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {
          // ignore
        }
      }
    }
  }, [])

  return { supported, listening, interimText, error, startListening, stopListening }
}
