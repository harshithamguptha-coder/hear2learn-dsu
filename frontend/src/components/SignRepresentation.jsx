import { findSignRepresentation } from '../services/signLanguage'

// Only exact normalized matches from the fixed phrase registry are rendered.
export default function SignRepresentation({ sessionId, text }) {
  if (!sessionId) return null
  const representation = findSignRepresentation(text)
  if (!representation) return null

  return (
    <figure className="sign-representation" data-sign-id={representation.id}>
      <figcaption>
        <span>Detected sign phrase</span>
        <strong>{representation.phrase}</strong>
      </figcaption>
      <img
        src={representation.asset}
        alt={`Placeholder sign representation for ${representation.phrase}`}
      />
      <small>Local MVP placeholder asset</small>
    </figure>
  )
}
