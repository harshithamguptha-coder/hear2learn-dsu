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
  const interimTextRef = useRef('')
  const [listening, setListening] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [error, setError] = useState('')
  const supported = Boolean(getSpeechRecognition())

  useEffect(() => {
    callbackRef.current = onFinalText
  }, [onFinalText])

  const createAndStart = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) {
      console.warn('[Speech] SpeechRecognition not supported in this browser.')
      return
    }

    // Clean up any lingering previous instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onstart = null
        recognitionRef.current.onresult = null
        recognitionRef.current.onerror = null
        recognitionRef.current.onend = null
        recognitionRef.current.abort()
      } catch (e) {
        console.warn('[Speech] Error cleaning previous instance:', e)
      }
      recognitionRef.current = null
    }

    console.log('[Speech] Initializing new SpeechRecognition instance...')
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      console.log('[Speech] onstart: microphone is actively listening.')
      setError('')
      setListening(true)
    }

    recognition.onresult = (event) => {
      let interim = ''
      let final = ''

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        const text = result[0]?.transcript || ''
        if (result.isFinal) {
          final += (final ? ' ' : '') + text
        } else {
          interim += (interim ? ' ' : '') + text
        }
      }

      console.log('[Speech] onresult -> final:', final, '| interim:', interim)

      interimTextRef.current = interim.trim()
      setInterimText(interim.trim())

      if (final.trim()) {
        interimTextRef.current = ''
        setInterimText('')
        console.log('[Speech] Finalizing text to callback:', final.trim())
        callbackRef.current(final.trim())
      }
    }

    recognition.onerror = (event) => {
      console.warn('[Speech] onerror:', event.error)

      // 'no-speech' is expected when the user pauses
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
      console.log('[Speech] onend. shouldListen:', shouldListenRef.current)
      setListening(false)

      // If speech ended with lingering interim text, finalize it
      if (interimTextRef.current) {
        const lingering = interimTextRef.current
        interimTextRef.current = ''
        setInterimText('')
        console.log('[Speech] onend finalizing lingering interim text:', lingering)
        callbackRef.current(lingering)
      } else {
        setInterimText('')
      }

      // Auto-restart if teacher kept microphone toggled on
      if (shouldListenRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (!shouldListenRef.current) return
          console.log('[Speech] Auto-restarting continuous listener...')
          createAndStart()
        }, 150)
      }
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
      console.log('[Speech] recognition.start() invoked successfully.')
    } catch (err) {
      console.error('[Speech] Failed to start recognition:', err)
      setError(`Could not start microphone: ${err.message}`)
      shouldListenRef.current = false
      setListening(false)
    }
  }, [])

  const startListening = useCallback(() => {
    console.log('[Speech] startListening button clicked.')
    if (!supported) return
    setError('')
    shouldListenRef.current = true
    createAndStart()
  }, [supported, createAndStart])

  const stopListening = useCallback(() => {
    console.log('[Speech] stopListening clicked.')
    shouldListenRef.current = false
    window.clearTimeout(restartTimerRef.current)
    setInterimText('')
    interimTextRef.current = ''
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch (e) {
        console.warn('[Speech] Error stopping recognition:', e)
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
