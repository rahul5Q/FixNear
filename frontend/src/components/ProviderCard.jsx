function ProviderCard({ name, service, rating, experience, location, onViewProfile }) {
  return (
    <div className="provider-card">

      <div className="provider-avatar">
        {name.charAt(0)}
      </div>

      <h3>{name}</h3>

      <p className="provider-service">
        {service}
      </p>

      <p>⭐ {rating} Rating</p>

      <p>{experience} experience</p>

      <p>📍 {location}</p>

      <button
  className="view-provider-btn"
  onClick={onViewProfile}
>
  View Profile
</button>

    </div>
  )
}

export default ProviderCard