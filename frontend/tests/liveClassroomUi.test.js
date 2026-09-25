import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const readSource = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8')

async function loadAiErrors() {
  return import('../src/services/aiErrors.js')
}

test('student live classroom renders captions before personalization without removed classroom tools', () => {
  const source = readSource('../src/components/StudentLiveWorkspace.jsx')
  assert.equal((source.match(/<TranscriptView/g) || []).length, 1)
  assert.equal(source.includes('LiveCaptionDock'), false)
  assert.equal(source.includes('mode-selector'), false)
  assert.equal(source.includes('FeaturePlacards'), false)
  assert.equal(source.includes('feature-placards'), false)

  const captionsIndex = source.indexOf('<TranscriptView')
  const personalizationIndex = source.indexOf('id="personalize-view"')
  assert.ok(captionsIndex >= 0 && captionsIndex < personalizationIndex)
  assert.match(source, /<SimplifiedLectureContent/)
  assert.match(source, /<TranslationLine/)
  assert.match(source, /<SignRepresentation/)
  assert.match(source, /<StructuredLectureView/)
  assert.match(source, /<LectureNotes/)
})

test('personalization remains a saved per-session student preference', () => {
  const workspace = readSource('../src/components/StudentLiveWorkspace.jsx')
  const page = readSource('../src/pages/StudentPage.jsx')
  assert.match(workspace, /id="personalize-view"/)
  assert.match(workspace, /onChange=\{\(event\) => onModeChange\(event\.target\.value\)\}/)
  assert.match(page, /saveAccessibilityPreference\(\s*sessionId,\s*nextMode,\s*nextLanguage,\s*token,?\s*\)/)
  assert.match(page, /getAccessibilityPreference\(sessionId, token\)/)
})

test('teacher lecture detail is scoped to one stored teacher session', () => {
  const detail = readSource('../src/components/TeacherLectureDetail.jsx')
  assert.match(detail, /lecture\.session_id === sessionId/)
  assert.match(detail, /getTranscript\(sessionId, token\)/)
  assert.match(detail, /getLectureNotes\(sessionId, token\)/)
  assert.match(detail, /Back to Recent Lectures/)
})

test('teacher live studio renders one captions surface from the existing transcript pipeline', () => {
  const studio = readSource('../src/components/TeacherLectureStudio.jsx')
  const page = readSource('../src/pages/TeacherPage.jsx')
  const hook = readSource('../src/hooks/useSpeechRecognition.js')
  assert.equal((studio.match(/<TranscriptView/g) || []).length, 1)
  assert.match(studio, /id="teacher-captions"/)
  assert.match(studio, /items=\{transcript\}/)
  assert.match(studio, /interimText=\{active \? interimText : ''\}/)
  assert.ok(studio.indexOf('className="studio-actions"') < studio.indexOf('{captions}'))
  assert.match(page, /transcript=\{transcript\} interimText=\{speech\.interimText\}/)
  assert.match(page, /saveTranscript\(sessionId, text\)/)
  assert.match(page, /sessionRef\.current\?\.session_id !== sessionId/)
  assert.equal((hook.match(/new SpeechRecognition\(\)/g) || []).length, 1)
})

test('AI quota failures use a safe fallback and stop automatic retries for that lecture', async () => {
  const { getAiFeatureError, isAiUnavailableError } = await loadAiErrors()
  const quotaError = {
    status: 503,
    message: 'AI structuring service unavailable: OpenAI API returned 429: credit_balance_exhausted',
  }
  assert.equal(isAiUnavailableError(quotaError), true)
  const safeMessage = getAiFeatureError(quotaError, 'AI lesson insights')
  assert.equal(safeMessage, 'AI lesson insights is temporarily unavailable. Your live captions and other accessibility features are still working.')
  assert.equal(safeMessage.includes('OpenAI'), false)
  assert.equal(safeMessage.includes('credit_balance_exhausted'), false)

  const page = readSource('../src/pages/StudentPage.jsx')
  const simplified = readSource('../src/components/SimplifiedLectureContent.jsx')
  const structured = readSource('../src/components/StructuredLectureView.jsx')
  assert.match(page, /aiUnavailableSessionRef\.current === sessionId/)
  assert.match(page, /if \(isAiUnavailableError\(error\)\) aiUnavailableSessionRef\.current = sessionId/)
  assert.match(page, /setStructureError\(getAiFeatureError\(error, 'AI lesson insights'\)\)/)
  assert.match(simplified, /className="message info ai-fallback-status" role="status"/)
  assert.match(structured, /getAiFeatureError\(err, 'The Lecture Assistant'\)/)
  assert.match(structured, /className="structured-banner fallback" role="status"/)
})

test('speech recognition uses one guarded instance and non-fatal reconnect scheduling', () => {
  const hook = readSource('../src/hooks/useSpeechRecognition.js')
  const studio = readSource('../src/components/TeacherLectureStudio.jsx')
  assert.equal((hook.match(/new SpeechRecognition\(\)/g) || []).length, 1)
  assert.match(hook, /event\.error === 'network'/)
  assert.match(hook, /scheduleRecognitionRestart/)
  assert.match(hook, /window\.clearTimeout\(restartTimerRef\.current\)/)
  assert.match(studio, /speech\.isReconnecting/)
  assert.match(studio, /Reconnecting microphone/)
})
