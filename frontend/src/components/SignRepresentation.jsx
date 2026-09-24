import { useEffect, useRef, useState } from 'react'

import { findSignRepresentation } from '../services/signLanguage'

const SVG_NAMESPACE = 'http://www.w3.org/2000/svg'

function getSvgRoot(objectRef) {
  return objectRef.current?.contentDocument?.documentElement || null
}

function isSvgDocument(objectRef) {
  return getSvgRoot(objectRef)?.namespaceURI === SVG_NAMESPACE
}

// Only exact normalized matches from the fixed phrase registry are rendered.
// The local animation is an illustrative phrase asset, not unrestricted
// sentence-to-sign translation. The original SVG remains a safe fallback.
export default function SignRepresentation({ sessionId, text }) {
  const objectRef = useRef(null)
  const animationCheckTimerRef = useRef(null)
  const desiredPlayingRef = useRef(true)
  const [animationFailed, setAnimationFailed] = useState(false)
  const [isPlaying, setIsPlaying] = useState(true)
  const representation = findSignRepresentation(text)

  useEffect(() => {
    desiredPlayingRef.current = true
    setAnimationFailed(false)
    setIsPlaying(true)
    return () => {
      if (animationCheckTimerRef.current) {
        window.clearTimeout(animationCheckTimerRef.current)
      }
    }
  }, [representation?.id])

  if (!sessionId || !representation) return null

  function runSvgAction(action) {
    const root = getSvgRoot(objectRef)
    if (!root || typeof root[action] !== 'function') return false
    try {
      root[action]()
      return true
    } catch {
      return false
    }
  }

  function setPlaying(nextPlaying) {
    desiredPlayingRef.current = nextPlaying
    setIsPlaying(nextPlaying)
    if (nextPlaying) runSvgAction('unpauseAnimations')
    else runSvgAction('pauseAnimations')
  }

  function handlePlay() {
    setPlaying(true)
  }

  function handlePause() {
    setPlaying(false)
  }

  function handleReplay() {
    desiredPlayingRef.current = true
    setIsPlaying(true)
    const root = getSvgRoot(objectRef)
    if (!root) return
    try {
      if (typeof root.setCurrentTime === 'function') root.setCurrentTime(0)
    } catch {
      // A browser may not expose the SVG timeline; the fallback remains usable.
    }
    runSvgAction('unpauseAnimations')
  }

  function handleAnimationLoad() {
    // Chrome can report object.onLoad once before the nested SVG document is
    // fully ready. Poll briefly so valid animations are not replaced by the
    // static fallback during that loading window.
    if (animationCheckTimerRef.current) {
      window.clearTimeout(animationCheckTimerRef.current)
    }
    const checkDocument = (attempt = 0) => {
      if (isSvgDocument(objectRef)) {
        setAnimationFailed(false)
        setIsPlaying(desiredPlayingRef.current)
        if (desiredPlayingRef.current) runSvgAction('unpauseAnimations')
        else runSvgAction('pauseAnimations')
        return
      }
      if (attempt >= 20) {
        setAnimationFailed(true)
        return
      }
      animationCheckTimerRef.current = window.setTimeout(() => checkDocument(attempt + 1), 50)
    }
    checkDocument()
  }

  return (
    <figure className="sign-representation" data-sign-id={representation.id}>
      <figcaption>
        <span>Detected sign phrase</span>
        <strong>{representation.phrase}</strong>
      </figcaption>

      <div className="sign-animation-frame">
        {animationFailed ? (
          <img
            src={representation.fallbackAsset || representation.asset}
            alt={`Static sign representation for ${representation.phrase}`}
          />
        ) : (
          <object
            ref={objectRef}
            data={representation.animationAsset}
            type="image/svg+xml"
            aria-label={`Local sign animation for ${representation.phrase}`}
            onLoad={handleAnimationLoad}
            onError={() => setAnimationFailed(true)}
          >
            <img
              src={representation.fallbackAsset || representation.asset}
              alt={`Static sign representation for ${representation.phrase}`}
            />
          </object>
        )}
      </div>

      <div className="sign-controls" aria-label={`Controls for ${representation.phrase} sign`}>
        <button
          className="sign-control-button"
          type="button"
          onClick={handlePlay}
          disabled={animationFailed || isPlaying}
          aria-label={`Play sign animation for ${representation.phrase}`}
        >
          ▶ Play
        </button>
        <button
          className="sign-control-button"
          type="button"
          onClick={handlePause}
          disabled={animationFailed || !isPlaying}
          aria-label={`Pause sign animation for ${representation.phrase}`}
        >
          ❚❚ Pause
        </button>
        <button
          className="sign-control-button"
          type="button"
          onClick={handleReplay}
          disabled={animationFailed}
          aria-label={`Replay sign animation for ${representation.phrase}`}
        >
          ↻ Replay
        </button>
      </div>
      <small>
        {animationFailed
          ? 'Animation unavailable; showing the static local fallback.'
          : 'Short local phrase animation — fixed supported phrases only.'}
      </small>
    </figure>
  )
}
