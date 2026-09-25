import LectureNotes from './LectureNotes'
import SimplifiedLectureContent from './SimplifiedLectureContent'
import SignRepresentation from './SignRepresentation'
import StatusBadge from './StatusBadge'
import StructuredLectureView from './StructuredLectureView'
import TranslationLine from './TranslationLine'
import { findSignRepresentation } from '../services/signLanguage'
import TranscriptView from './TranscriptView'

const MODE_OPTIONS = [
  ['standard', 'Standard'],
  ['simplified', 'Simplified'],
  ['translation', 'Translation'],
  ['sign_support', 'Sign Support'],
]

export default function StudentLiveWorkspace({
  user,
  session,
  transcript,
  connectionLabel,
  accessibilityMode,
  onModeChange,
  translationLanguage,
  onTranslationLanguageChange,
  preferenceAvailable,
  preferenceLoading,
  preferenceSaving,
  preferenceError,
  onLeave,
  leaving,
  structuredData,
  structuring,
  structureError,
  notes,
  notesLoading,
  notesError,
  qaResult,
  setQaResult,
  questionInput,
  setQuestionInput,
  conversationId,
  setConversationId,
  conversationMessages,
  setConversationMessages,
}) {
  return (
    <div className="view-stack live-workspace">
      <section className="live-classroom-header">
        <div className="live-classroom-title"><StatusBadge status={session.status} /><div><p className="eyebrow">{session.status === 'active' ? 'Live classroom' : 'Lecture complete'}</p><h1>{session.title || 'Untitled Lecture'}</h1><p>{user?.name ? `${user.name}'s learning view` : 'Your learning view'} <span aria-hidden="true">·</span> Session {session.session_id}</p></div></div>
        <div className="live-classroom-actions"><span className="connection-state" role="status"><span className="connection-dot" aria-hidden="true" />{connectionLabel}</span>{session.status === 'active' && <button className="secondary-button leave-button" type="button" onClick={onLeave} disabled={leaving}>{leaving ? 'Leaving…' : 'Leave lecture'}</button>}</div>
      </section>

      <TranscriptView id="captions-section" items={transcript} emptyText="The transcript will appear here as soon as the teacher starts speaking." isLive={session.status === 'active'} />

      <section className="learning-mode-section personalization-section" aria-labelledby="learning-mode-title">
        <div><p className="eyebrow">Personalize your view</p><h2 id="learning-mode-title">Choose your learning mode</h2><p>Your preference is saved only for your account in this lecture.</p></div>
        <div className="personalization-control"><label htmlFor="personalize-view">Personalize your view</label><select id="personalize-view" value={accessibilityMode} onChange={(event) => onModeChange(event.target.value)} disabled={!preferenceAvailable || preferenceLoading || preferenceSaving} aria-describedby="personalization-status">{MODE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
        {accessibilityMode === 'translation' && <div className="translation-setting"><label htmlFor="translation-language">Translation language</label><select id="translation-language" value={translationLanguage} onChange={(event) => onTranslationLanguageChange(event.target.value)} disabled={preferenceSaving}><option value="kn">Kannada</option><option value="hi">Hindi</option><option value="te">Telugu</option></select><span>Original English stays visible.</span></div>}
        <p id="personalization-status" className={`accessibility-save-status ${preferenceError ? 'error' : ''}`} role="status" aria-live="polite">{preferenceError || (preferenceLoading ? 'Loading your saved mode…' : preferenceSaving ? 'Saving your mode…' : 'Saved for this lecture.')}</p>
      </section>

      {accessibilityMode === 'simplified' && <section className="workspace-section simplified-content-block" aria-labelledby="simplified-content-title"><div className="subsection-heading"><div><p className="eyebrow">Additional learning support</p><h3 id="simplified-content-title">Simplified view</h3></div><span>Built from the saved transcript</span></div><SimplifiedLectureContent items={transcript} structuredData={structuredData} loading={structuring} error={structureError} /></section>}
      {accessibilityMode === 'translation' && <section className="workspace-section selected-feature-content" id="translation-content" aria-labelledby="translation-content-title"><div className="subsection-heading"><div><p className="eyebrow">Selected feature</p><h3 id="translation-content-title">Translation</h3></div><span>{translationLanguage.toUpperCase()}</span></div>{transcript.length ? <div className="translation-list">{transcript.map((item) => <TranslationLine key={item.id} sessionId={session.session_id} text={item.text} language={translationLanguage} />)}</div> : <p className="muted-copy">Translations will appear as the teacher speaks.</p>}</section>}
      {accessibilityMode === 'sign_support' && <section className="workspace-section selected-feature-content" id="sign-content" aria-labelledby="sign-content-title"><div className="subsection-heading"><div><p className="eyebrow">Selected feature</p><h3 id="sign-content-title">Sign Support</h3></div><span>{transcript.filter((item) => findSignRepresentation(item.text)).length} supported phrases</span></div>{transcript.some((item) => findSignRepresentation(item.text)) ? <div className="sign-support-list">{transcript.map((item) => <SignRepresentation key={item.id} sessionId={session.session_id} text={item.text} />)}</div> : <p className="muted-copy">Supported sign phrases will appear as the teacher speaks.</p>}</section>}

      <section className="workspace-section intelligence-section" id="intelligence-section" tabIndex="-1" aria-labelledby="intelligence-title">
        <div className="section-heading-row"><div><p className="eyebrow">AI classroom intelligence</p><h2 id="intelligence-title">Understand the important ideas</h2></div><span className="section-caption">Structured from this lecture only</span></div>
        <StructuredLectureView structuredData={structuredData} loading={structuring} error={structureError} sessionId={session.session_id} qaResult={qaResult} setQaResult={setQaResult} questionInput={questionInput} setQuestionInput={setQuestionInput} conversationId={conversationId} setConversationId={setConversationId} conversationMessages={conversationMessages} setConversationMessages={setConversationMessages} />
      </section>

      <section className="workspace-section" id="notes-section" tabIndex="-1" aria-label="Lecture notes">
        {(notes || notesLoading || notesError) ? <LectureNotes notes={notes} loading={notesLoading} error={notesError} /> : <div className="empty-state empty-state-card"><span className="empty-state-icon" aria-hidden="true">▤</span><h3>Notes are created when the lecture ends</h3><p>Keep listening live. Your saved transcript and generated notes will stay available here.</p></div>}
      </section>
    </div>
  )
}
