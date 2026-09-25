export default function StudentJoin({ input, onInputChange, onSubmit, joining, error }) {
  return (
    <div className="join-view">
      <section className="join-hero">
        <div className="join-hero-art" aria-hidden="true"><span>✦</span><i>Live learning</i><b>01</b></div>
        <div className="join-hero-copy"><p className="eyebrow">Connect to your classroom</p><h1>Join a live lecture</h1><p>Enter the session ID shared by your teacher. Your attendance and personal lecture history are saved automatically.</p></div>
      </section>
      <section className="join-card-large" aria-labelledby="join-lecture-title">
        <div className="join-card-heading"><span className="join-card-icon" aria-hidden="true">＋</span><div><p className="eyebrow">Live classroom access</p><h2 id="join-lecture-title">Enter your session ID</h2></div></div>
        <form onSubmit={onSubmit}>
          <label htmlFor="session-id">Lecture session ID</label>
          <div className="join-row"><input id="session-id" name="session-id" value={input} onChange={onInputChange} placeholder="For example: 9A7F3C21" autoComplete="off" autoCapitalize="characters" spellCheck="false" maxLength={16} aria-describedby="session-help" /><button className="primary-button" type="submit" disabled={joining}>{joining ? 'Joining…' : 'Join lecture'}</button></div>
          <p id="session-help" className="field-help">Your teacher’s ID uses letters and numbers. You can join only while the lecture is live.</p>
        </form>
        {error && <p className="message error" role="alert">{error}</p>}
      </section>
    </div>
  )
}
