// Fixed MVP phrase registry. Add future phrases here with one local asset each.
const SIGN_PHRASES = [
  {
    id: 'good-morning',
    phrase: 'Good morning',
    asset: '/signs/good-morning.svg',
  },
  {
    id: 'open-your-book',
    phrase: 'Open your book',
    asset: '/signs/open-your-book.svg',
  },
  {
    id: 'pay-attention',
    phrase: 'Pay attention',
    asset: '/signs/pay-attention.svg',
  },
  {
    id: 'any-questions',
    phrase: 'Any questions?',
    asset: '/signs/any-questions.svg',
  },
  {
    id: 'thank-you',
    phrase: 'Thank you',
    asset: '/signs/thank-you.svg',
  },
]

function normalizePhrase(text) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[.!?,;:]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function findSignRepresentation(text) {
  if (typeof text !== 'string') return null
  const normalizedText = normalizePhrase(text)
  return (
    SIGN_PHRASES.find(
      (representation) => normalizePhrase(representation.phrase) === normalizedText,
    ) || null
  )
}

export { SIGN_PHRASES }
