// Simplified mode works only from the saved transcript and structured data.
// It deliberately does not create another speech-recognition or translation path.
const SIMPLE_PHRASES = [
  [/\bin order to\b/gi, 'to'],
  [/\bfor the purpose of\b/gi, 'to'],
  [/\bwith the goal of\b/gi, 'to'],
  [/\ba number of\b/gi, 'several'],
  [/\bprior to\b/gi, 'before'],
  [/\bsubsequently\b/gi, 'then'],
  [/\butili[sz]e[ds]?\b/gi, 'use'],
  [/\bapproximately\b/gi, 'about'],
  [/\badditional\b/gi, 'more'],
  [/\bmethodology\b/gi, 'method'],
  [/\bindividuals\b/gi, 'people'],
  [/\bcommence[sd]?\b/gi, 'start'],
  [/\bterminate[sd]?\b/gi, 'end'],
  [/\bascertain\b/gi, 'find out'],
  [/\bendeavou?r\b/gi, 'try'],
  [/\bcomprehend\b/gi, 'understand'],
]

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function uniqueTerms(values) {
  const seen = new Set()
  return (Array.isArray(values) ? values : [])
    .map((value) => (typeof value === 'string' ? value.trim() : ''))
    .filter((value) => {
      if (!value) return false
      const key = value.toLocaleLowerCase()
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

function protectTechnicalTerms(text, technicalTerms) {
  const replacements = []
  const protectedText = technicalTerms.reduce((current, term, index) => {
    const token = `__LECTURE_TERM_${index}__`
    if (!current.toLocaleLowerCase().includes(term.toLocaleLowerCase())) return current
    replacements.push({ token, term })
    return current.replace(new RegExp(escapeRegExp(term), 'gi'), token)
  }, text)

  return { protectedText, replacements }
}

function restoreTechnicalTerms(text, replacements) {
  return replacements.reduce(
    (current, replacement) => current.split(replacement.token).join(replacement.term),
    text,
  )
}

export function simplifyText(text, technicalTerms = []) {
  if (typeof text !== 'string' || !text.trim()) return ''

  const { protectedText, replacements } = protectTechnicalTerms(
    text.trim(),
    uniqueTerms(technicalTerms),
  )
  const simplified = SIMPLE_PHRASES.reduce(
    (current, [pattern, replacement]) => current.replace(pattern, replacement),
    protectedText,
  )
  const restored = restoreTechnicalTerms(simplified, replacements)
    .replace(/\s+/g, ' ')
    .trim()
  return restored.charAt(0).toLocaleUpperCase() + restored.slice(1)
}

export function buildSimplifiedLecture(items = [], structuredData = null) {
  const technicalTerms = uniqueTerms([
    ...(structuredData?.technical_terms || []),
    ...(structuredData?.concepts || []),
  ])
  const transcriptText = (Array.isArray(items) ? items : [])
    .map((item) => (typeof item?.text === 'string' ? item.text : ''))
    .filter(Boolean)
    .join(' ')
  const sourceText = structuredData?.clean_text?.trim() || transcriptText
  const keyPoints = uniqueTerms(structuredData?.key_points)
    .map((point) => simplifyText(point, technicalTerms))
    .filter(Boolean)

  return {
    hasContent: Boolean(sourceText.trim() || keyPoints.length),
    text: simplifyText(sourceText, technicalTerms),
    keyPoints,
    technicalTerms,
  }
}
