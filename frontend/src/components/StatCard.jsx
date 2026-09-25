export default function StatCard({ icon, label, value, detail, tone = 'blue' }) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <div className="stat-card-topline">
        <span className="stat-icon" aria-hidden="true">{icon}</span>
        {detail && <span className="stat-detail">{detail}</span>}
      </div>
      <strong className="stat-value">{value}</strong>
      <span className="stat-label">{label}</span>
    </article>
  )
}
