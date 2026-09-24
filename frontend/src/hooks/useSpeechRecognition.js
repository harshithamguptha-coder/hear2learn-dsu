import { useCallback, useEffect, useRef, useState } from 'react'

const RECOGNITION_ERRORS = {
  'audio-capture': 'No speech-recognition microphone was found.',
  'not-allowed': 'Speech recognition is not allowed. Check the browser microphone permission.',
  'network': 'Speech recognition lost its network connection.',
  'service-not-allowed': 'The browser blocked the speech-recognition service.',
  'language-not-supported': 'The browser does not support the selected speech language.',
}

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function getMicrophoneError(error) {
  const messages = {
    AbortError: 'Microphone startup was interrupted. Please try again.',
    NotAllowedError: 'Microphone permission was denied. Allow access in your browser and try again.',
    NotFoundError: 'No microphone was found. Connect a microphone and try again.',
    NotReadableError: 'The microphone is already in use or cannot be read.',
    OverconstrainedError: 'The selected microphone does not support the requested audio settings.',
    SecurityError: 'Microphone access was blocked by browser security settings.',
  }
  return messages[error?.name] || 'The microphone could not be started. Please try again.'
}

function stopMediaStream(stream) {
  stream?.getTracks().forEach((track) => track.stop())
}

// getUserMedia explicitly acquires and holds microphone permission. Web Speech
// then provides the fast browser-based STT for the MVP.
export function useSpeechRecognition(onFinalText) {
  const recognitionRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const callbackRef = useRef(onFinalText)
  const shouldListenRef = useRef(false)
  const restartTimerRef = useRef(null)
  const requestIdRef = useRef(0)
  const [isListening, setIsListening] = useState(false)
  const [isRequesting, setIsRequesting] = useState(false)
  const [microphoneOn, setMicrophoneOn] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [error, setError] = useState('')

  const recognitionSupported = Boolean(getSpeechRecognition())
  const microphoneSupported =
    typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
  const supported = recognitionSupported && microphoneSupported
  const supportError = !microphoneSupported
    ? 'Microphone access requires a supported browser on HTTPS or localhost.'
    : !recognitionSupported
      ? 'This browser does not support Web Speech recognition. Use a current Chrome or Edge browser.'
      : ''

  useEffect(() => {
    callbackRef.current = onFinalText
  }, [onFinalText])

  const releaseMicrophone = useCallback(() => {
    stopMediaStream(mediaStreamRef.current)
    mediaStreamRef.current = null
    setMicrophoneOn(false)
    setIsListening(false)
  }, [])

  const stopListening = useCallback(() => {
    shouldListenRef.current = false
    requestIdRef.current += 1
    window.clearTimeout(restartTimerRef.current)

    const recognition = recognitionRef.current
    recognitionRef.current = null
    try {
      recognition?.stop()
    } catch {
      // Recognition may already be stopped by the browser.
    }

    setInterimText('')
    setIsRequesting(false)
    releaseMicrophone()
  }, [releaseMicrophone])

  const startListening = useCallback(async () => {
    if (isRequesting || microphoneOn) return

    if (!supported) {
      setError(supportError)
      return
    }

    const SpeechRecognition = getSpeechRecognition()
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    shouldListenRef.current = true
    setError('')
    setIsRequesting(true)

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (requestId !== requestIdRef.current || !shouldListenRef.current) {
        stopMediaStream(mediaStream)
        return
      }

      mediaStreamRef.current = mediaStream
      setMicrophoneOn(true)

      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      recognitionRef.current = recognition

      recognition.onstart = () => {
        setError('')
        setIsListening(true)
      }

      recognition.onresult = (event) => {
        const finalParts = []
        const interimParts = []

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index]
          const text = result[0].transcript.trim()
          if (!text) continue
          if (result.isFinal) finalParts.push(text)
          else interimParts.push(text)
        }

        setInterimText(interimParts.join(' '))
        const finalText = finalParts.join(' ')
        if (finalText) callbackRef.current(finalText)
      }

      recognition.onerror = (event) => {
        if (event.error === 'aborted' || event.error === 'no-speech') return

        shouldListenRef.current = false
        requestIdRef.current += 1
        window.clearTimeout(restartTimerRef.current)
        recognitionRef.current = null
        releaseMicrophone()
        setError(RECOGNITION_ERRORS[event.error] || 'Speech recognition stopped unexpectedly.')
      }

      recognition.onend = () => {
        setIsListening(false)
        setInterimText('')
        if (recognitionRef.current !== recognition) return
        if (!shouldListenRef.current || !mediaStreamRef.current) return

        restartTimerRef.current = window.setTimeout(() => {
          if (!shouldListenRef.current || !mediaStreamRef.current) return
          try {
            recognition.start()
          } catch {
            shouldListenRef.current = false
            recognitionRef.current = null
            releaseMicrophone()
            setError('Speech recognition could not restart. Please enable it again.')
          }
        }, 300)
      }

      recognition.start()
    } catch (mediaError) {
      const recognitionStartFailed = Boolean(recognitionRef.current)
      shouldListenRef.current = false
      requestIdRef.current += 1
      window.clearTimeout(restartTimerRef.current)
      recognitionRef.current = null
      releaseMicrophone()
      setIsRequesting(false)
      if (recognitionStartFailed) {
        setError('The browser could not start speech recognition after microphone access was granted.')
      } else {
        setError(getMicrophoneError(mediaError))
      }
    } finally {
      if (requestId === requestIdRef.current) setIsRequesting(false)
    }
  }, [isRequesting, microphoneOn, releaseMicrophone, supportError, supported])

  useEffect(() => () => {
    shouldListenRef.current = false
    requestIdRef.current += 1
    window.clearTimeout(restartTimerRef.current)
    try {
      recognitionRef.current?.abort()
    } catch {
      // The browser may already have stopped recognition.
    }
    recognitionRef.current = null
    stopMediaStream(mediaStreamRef.current)
    mediaStreamRef.current = null
  }, [])

  return {
    supported,
    supportError,
    isListening,
    isRequesting,
    microphoneOn,
    interimText,
    error,
    startListening,
    stopListening,
  }
}
