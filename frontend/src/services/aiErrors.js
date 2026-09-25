const AI_UNAVAILABLE_STATUSES = new Set([429, 500, 502, 503, 504])
const PROVIDER_ERROR_PATTERN = /(openai|quota|credit|insufficient[_ ]quota|credit_balance_exhausted|ai (structuring|assistant|provider))/i

export function isAiUnavailableError(error) {
  const status = Number(error?.status)
  if (AI_UNAVAILABLE_STATUSES.has(status)) return true
  return PROVIDER_ERROR_PATTERN.test(error?.message || '')
}

export function getAiFeatureError(error, feature = 'This AI feature') {
  if (isAiUnavailableError(error)) {
    return `${feature} is temporarily unavailable. Your live captions and other accessibility features are still working.`
  }
  return `${feature} could not complete this request. Please try again.`
}
