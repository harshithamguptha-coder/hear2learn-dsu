// Fixed MVP phrase registry. Add future phrases here with one local asset each.
// Phrase matching stays exact and normalized; this is not sentence translation.
const SIGN_PHRASES = [
  {
    id: 'good-morning',
    phrase: 'Good morning',
    asset: '/signs/good-morning.svg',
    fallbackAsset: '/signs/good-morning.svg',
    animationAsset: '/signs/animations/good-morning.animation.svg',
  },
  {
    id: 'open-your-book',
    phrase: 'Open your book',
    asset: '/signs/open-your-book.svg',
    fallbackAsset: '/signs/open-your-book.svg',
    animationAsset: '/signs/animations/open-your-book.animation.svg',
  },
  {
    id: 'pay-attention',
    phrase: 'Pay attention',
    asset: '/signs/pay-attention.svg',
    fallbackAsset: '/signs/pay-attention.svg',
    animationAsset: '/signs/animations/pay-attention.animation.svg',
  },
  {
    id: 'any-questions',
    phrase: 'Any questions?',
    asset: '/signs/any-questions.svg',
    fallbackAsset: '/signs/any-questions.svg',
    animationAsset: '/signs/animations/any-questions.animation.svg',
  },
  {
    id: 'thank-you',
    phrase: 'Thank you',
    asset: '/signs/thank-you.svg',
    fallbackAsset: '/signs/thank-you.svg',
    animationAsset: '/signs/animations/thank-you.animation.svg',
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
