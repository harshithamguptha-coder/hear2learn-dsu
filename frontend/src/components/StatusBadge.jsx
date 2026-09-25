const STATUS_LABELS = {
  active: 'LIVE',
  live: 'LIVE',
  ended: 'ENDED',
  inactive: 'INACTIVE',
  in_progress: 'LIVE',
  attended: 'ATTENDED',
}

export default function StatusBadge({ status = 'inactive', label, attendance = false }) {
  const normalized = String(status || 'inactive').toLowerCase()
  const text = label || (attendance
    ? { in_progress: 'ATTENDING', attended: 'ATTENDED', active: 'LIVE', ended: 'ENDED' }[normalized]
    : STATUS_LABELS[normalized]) || String(status || 'Inactive')
  return (
    <span className={`status-badge ${normalized} ${attendance ? 'attendance-badge' : ''}`}>
      <span className="status-dot" aria-hidden="true" />
      {text}
    </span>
  )
}
