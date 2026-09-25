import { Link } from 'react-router-dom'
import { useState } from 'react'

const NAV_ITEMS = {
  teacher: [
    { key: 'overview', label: 'Overview', icon: '⌂' },
    { key: 'lectures', label: 'Recent Lectures', icon: '▤' },
    { key: 'new', label: 'Start New Lecture', icon: '＋' },
    { key: 'analytics', label: 'Lecture Analytics', icon: '▥' },
  ],
  student: [
    { key: 'overview', label: 'Overview', icon: '⌂' },
    { key: 'lectures', label: 'My Lectures', icon: '▤' },
    { key: 'join', label: 'Join New Lecture', icon: '＋' },
  ],
}

function getInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || 'A'
}

function Sidebar({ role, activeView, onLogout, mobileOpen, onClose }) {
  const base = role === 'teacher' ? '/teacher' : '/student'
  const items = NAV_ITEMS[role] || []

  return (
    <aside className={`app-sidebar ${mobileOpen ? 'is-open' : ''}`} aria-label={`${role} navigation`}>
      <div className="sidebar-brand-wrap">
        <Link className="sidebar-brand" to={`${base}?view=overview`} onClick={onClose}>
          <span className="brand-mark" aria-hidden="true">A</span>
          <span>
            <strong>Accessible</strong>
            <small>Classroom</small>
          </span>
        </Link>
        <button className="sidebar-close" type="button" onClick={onClose} aria-label="Close navigation">
          ×
        </button>
      </div>

      <div className="sidebar-context">
        <span className="sidebar-context-icon" aria-hidden="true">{role === 'teacher' ? 'T' : 'S'}</span>
        <span>
          <small>{role === 'teacher' ? 'Teacher workspace' : 'Student workspace'}</small>
          <strong>AI learning space</strong>
        </span>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        <p className="sidebar-label">Workspace</p>
        {items.map((item) => {
          const isActive = activeView === item.key
          return (
            <Link
              key={item.key}
              className={`sidebar-link ${isActive ? 'active' : ''}`}
              to={`${base}?view=${item.key}`}
              aria-current={isActive ? 'page' : undefined}
              onClick={onClose}
            >
              <span className="sidebar-link-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="sidebar-bottom">
        <p className="sidebar-label">Account</p>
        <button className="sidebar-link sidebar-logout" type="button" onClick={onLogout}>
          <span className="sidebar-link-icon" aria-hidden="true">↪</span>
          <span>Log out</span>
        </button>
      </div>
    </aside>
  )
}

function Topbar({ user, role, liveLecture, onMenu }) {
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const formattedDate = new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date())

  return (
    <header className="app-topbar">
      <div className="topbar-leading">
        <button className="mobile-menu-button" type="button" onClick={onMenu} aria-label="Open navigation">
          <span aria-hidden="true">☰</span>
        </button>
        <div>
          <p className="topbar-greeting">{greeting}, {user?.name || 'there'}</p>
          <p className="topbar-date">{formattedDate}</p>
        </div>
      </div>
      <div className="topbar-actions">
        {liveLecture && (
          <span className="topbar-live" role="status">
            <span className="live-pulse" aria-hidden="true" />
            <span><strong>Live now</strong><small>{liveLecture.title || 'Current lecture'}</small></span>
          </span>
        )}
        <span className="topbar-divider" aria-hidden="true" />
        <div className="profile-chip">
          <span className="profile-avatar" aria-hidden="true">{getInitials(user?.name)}</span>
          <span className="profile-copy">
            <strong>{user?.name || 'Account'}</strong>
            <small>{role === 'teacher' ? 'Teacher' : 'Student'}</small>
          </span>
        </div>
      </div>
    </header>
  )
}

export default function AppShell({ user, role, activeView, liveLecture, onLogout, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)

  function closeMobileNav() {
    setMobileOpen(false)
  }

  return (
    <div className="app-shell">
      <Sidebar
        role={role}
        activeView={activeView}
        onLogout={onLogout}
        mobileOpen={mobileOpen}
        onClose={closeMobileNav}
      />
      {mobileOpen && <button className="sidebar-backdrop" type="button" onClick={closeMobileNav} aria-label="Close navigation" />}
      <div className="app-workspace">
        <Topbar user={user} role={role} liveLecture={liveLecture} onMenu={() => setMobileOpen(true)} />
        <main className="workspace-main">{children}</main>
      </div>
    </div>
  )
}
