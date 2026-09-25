export default function EmptyState({ icon = '◌', title, description, action = null }) {
  return (
    <div className="empty-state empty-state-card">
      <span className="empty-state-icon" aria-hidden="true">{icon}</span>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}
