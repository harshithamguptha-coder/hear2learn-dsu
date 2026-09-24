import { useCallback, useEffect, useRef, useState } from 'react'

const ERROR_MESSAGES = {
  'audio-capture': 'No microphone was found. Check your microphone settings.',
  'not-allowed': 'Microphone access was blocked. Allow access and try again.',
  'network': 'Speech recognition lost its network connection. Please try again.',
  'service-not-allowed': 'This browser could not start speech recognition.',
  'language-not-supported': 'This browser does not support the selected speech language.',
}

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

// The browser captures microphone audio and performs the small STT step.
// Only finalized text is sent onward; interim words stay local.
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

  useEffect(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) return undefined

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
      if (final.trim()) callbackRef.current(final.trim())
    }

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        setError(
          ERROR_MESSAGES[event.error] ||
            'Speech recognition stopped unexpectedly. Please try again.',
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

      // Some browsers stop after a short pause. Restart while the teacher
      // has explicitly kept microphone listening switched on.
      if (shouldListenRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          try {
            recognition.start()
          } catch {
            shouldListenRef.current = false
          }
        }, 300)
      }
    }

    recognitionRef.current = recognition
    return () => {
      shouldListenRef.current = false
      window.clearTimeout(restartTimerRef.current)
      recognition.abort()
      recognitionRef.current = null
    }
  }, [])

  const startListening = useCallback(() => {
    if (!recognitionRef.current || !supported) return
    setError('')
    shouldListenRef.current = true
    try {
      recognition.start()
    } catch {
      // Calling start while it is already running is harmless.
    }
  }, [supported])

  const stopListening = useCallback(() => {
    shouldListenRef.current = false
    window.clearTimeout(restartTimerRef.current)
    setInterimText('')
    recognitionRef.current?.stop()
  }, [])

  return { supported, listening, interimText, error, startListening, stopListening }
}
