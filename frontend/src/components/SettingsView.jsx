export default function SettingsView({ user, role, onLogout }) {
  return (
    <div className="view-stack settings-view">
      <section className="page-intro"><div><p className="eyebrow">Account preferences</p><h1>Settings</h1><p>Your account and classroom preferences are managed securely for this session.</p></div></section>
      <section className="settings-card"><div className="settings-profile"><span className="settings-avatar" aria-hidden="true">{(user?.name || 'A').slice(0, 1).toUpperCase()}</span><div><p className="eyebrow">Signed in as</p><h2>{user?.name}</h2><p>{user?.email}</p></div></div><div className="settings-facts"><div><span>Role</span><strong>{role === 'teacher' ? 'Teacher' : 'Student'}</strong></div><div><span>Data scope</span><strong>Only your account</strong></div></div><p className="settings-note">Lecture history, attendance, and accessibility preferences are tied to your logged-in account. Use Log out to switch accounts safely.</p><button className="secondary-button" type="button" onClick={onLogout}>Log out</button></section>
    </div>
  )
}
