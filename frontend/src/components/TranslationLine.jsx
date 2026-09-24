import { useEffect, useState } from 'react'

import { translateTranscript } from '../api/client'

const LANGUAGE_NAMES = {
  en: 'English',
  kn: 'Kannada',
  hi: 'Hindi',
}

// Each original transcript item owns its translation request. Switching the
// language cancels stale work, while failures affect only the translation line.
export default function TranslationLine({ sessionId, text, language }) {
  const [state, setState] = useState({
    language: 'en',
    status: 'idle',
    text: '',
    error: '',
  })

  useEffect(() => {
    if (!sessionId || language === 'en' || !text) {
      setState({ language, status: 'idle', text: '', error: '' })
      return undefined
    }

    let cancelled = false
    setState({ language, status: 'loading', text: '', error: '' })

    translateTranscript(sessionId, text, language)
      .then((result) => {
        if (!cancelled) {
          setState({
            language,
            status: 'ready',
            text: result.translated_text,
            error: '',
          })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ language, status: 'error', text: '', error: error.message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [language, sessionId, text])

  if (language === 'en') return null

  // Do not display the previous language's text during the first render after
  // a selector change; the effect for the new language has not run yet.
  const visibleState = state.language === language
    ? state
    : { status: 'loading', text: '', error: '' }

  return (
    <div className="translation-line" lang={language} aria-live="polite">
      <span className="translation-label">{LANGUAGE_NAMES[language]} translation</span>
      {visibleState.status === 'loading' && (
        <p className="translation-loading">Translating…</p>
      )}
      {visibleState.status === 'ready' && <p>{visibleState.text}</p>}
      {visibleState.status === 'error' && (
        <p className="translation-error" role="status">
          Translation unavailable. The original English is still shown.
        </p>
      )}
    </div>
  )
}
