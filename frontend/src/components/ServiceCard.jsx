function ServiceCard({ icon, title, description, onClick, isSelected }) {
  return (
    <div
      className={`service-card ${isSelected ? 'service-card-active' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onClick()
        }
      }}
    >
      <div className="service-icon">{icon}</div>

      <h3>{title}</h3>

      <p>{description}</p>

      {onClick && (
        <div className="service-card-footer">
          <span className="service-card-badge">
            {isSelected ? '✓ Filter Applied' : 'Filter by Service →'}
          </span>
        </div>
      )}
    </div>
  )
}

export default ServiceCard