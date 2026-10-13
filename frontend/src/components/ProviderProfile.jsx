
import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

function ProviderProfile({
  provider,
  user,
  onBack,
  onBookNow,
  onManageBookings,
  onDashboard
}) {
  const [reviews, setReviews] = useState([])
  const [loadingReviews, setLoadingReviews] = useState(true)

  useEffect(() => {
    let isMounted = true

    if (provider?.name) {
      fetch(
        `${API_BASE_URL}/reviews?provider=${encodeURIComponent(provider.name)}`
      )
        .then((res) => res.json())
        .then((data) => {
          if (isMounted) {
            if (Array.isArray(data)) {
              setReviews(data)
            }
            setLoadingReviews(false)
          }
        })
        .catch((err) => {
          console.error('Error fetching provider reviews:', err)
          if (isMounted) {
            setLoadingReviews(false)
          }
        })
    }

    return () => {
      isMounted = false
    }
  }, [provider?.name])

  if (!provider) {
    return (
      <div className="provider-profile">
        <p>Provider details not available.</p>
        <button onClick={onBack}>Go Back</button>
      </div>
    )
  }

  const totalReviews = reviews.length
  const avgRating =
    totalReviews > 0
      ? (reviews.reduce((acc, r) => acc + r.rating, 0) / totalReviews).toFixed(1)
      : null

  return (
    <div className="provider-profile">
      <div className="provider-profile-card">
        <div className="provider-profile-avatar">
          {provider.name.charAt(0)}
        </div>

        <h1>{provider.name}</h1>
        <p className="provider-profile-service">
          {provider.service}
        </p>

        {avgRating ? (
          <p className="provider-rating-stat">
            ⭐ <strong>{avgRating}</strong> / 5 Customer Rating ({totalReviews}{' '}
            {totalReviews === 1 ? 'review' : 'reviews'})
          </p>
        ) : (
          <p className="provider-rating-stat">
            ⭐ {provider.rating} Rating (No customer reviews yet)
          </p>
        )}

        <p>💼 {provider.experience} experience</p>
        <p>📍 {provider.location}</p>

        <div className="provider-profile-actions">
          <button type="button" onClick={onBack}>Back</button>
          <button type="button" onClick={onBookNow}>Book Now</button>
          {user && onDashboard && (
            <button
              type="button"
              className="provider-dashboard-btn"
              onClick={onDashboard}
            >
              Dashboard
            </button>
          )}
          {onManageBookings && (
            <button
              type="button"
              onClick={() => onManageBookings(provider)}
              style={{ background: '#475569' }}
            >
              Provider Bookings
            </button>
          )}
        </div>

        {/* Customer Reviews Section */}
        <div className="provider-reviews-section">
          <h3>Customer Reviews ({totalReviews})</h3>
          {loadingReviews ? (
            <p>Loading reviews...</p>
          ) : totalReviews === 0 ? (
            <div className="no-reviews-box">
              <p>No customer reviews yet for this provider.</p>
              <p className="no-reviews-sub">
                Completed bookings can be reviewed by customers in My Bookings.
              </p>
            </div>
          ) : (
            <div className="reviews-list">
              {reviews.map((rev) => (
                <div className="review-card" key={rev.id}>
                  <div className="review-card-top">
                    <span className="review-card-stars">
                      {'★'.repeat(rev.rating)}
                      {'☆'.repeat(5 - rev.rating)}
                    </span>
                    <span className="review-card-score">{rev.rating}/5</span>
                    <span className="review-card-author">{rev.customer_email}</span>
                  </div>
                  {rev.comment && (
                    <p className="review-card-comment">&ldquo;{rev.comment}&rdquo;</p>
                  )}
                  {rev.created_at && (
                    <span className="review-card-date">
                      {new Date(rev.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProviderProfile
