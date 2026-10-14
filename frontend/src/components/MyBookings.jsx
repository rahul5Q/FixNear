import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

function MyBookings({ user, token, onBackToDashboard }) {
  const [bookings, setBookings] = useState([])
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [cancellingId, setCancellingId] = useState(null)
  const [message, setMessage] = useState('')

  const authToken = token || localStorage.getItem('token')

  // Rating & review state
  const [activeRatingBookingId, setActiveRatingBookingId] = useState(null)
  const [currentRating, setCurrentRating] = useState(5)
  const [hoverRating, setHoverRating] = useState(0)
  const [reviewComment, setReviewComment] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)
  const [reviewError, setReviewError] = useState('')

  const ratingLabels = {
    1: '1 star - Poor',
    2: '2 stars - Fair',
    3: '3 stars - Good',
    4: '4 stars - Very Good',
    5: '5 stars - Excellent'
  }

  useEffect(() => {
    if (!user?.email) return
    let isMounted = true

    const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {}

    fetch(
      `${API_BASE_URL}/bookings?user_email=${encodeURIComponent(user.email)}`,
      { headers }
    )
      .then((response) => response.json())
      .then((data) => {
        if (isMounted) {
          setBookings(Array.isArray(data) ? data : [])
          setLoading(false)
        }
      })
      .catch((error) => {
        console.error('Error fetching bookings:', error)
        if (isMounted) {
          setLoading(false)
        }
      })

    fetch(
      `${API_BASE_URL}/reviews?customer_email=${encodeURIComponent(user.email)}`
    )
      .then((response) => response.json())
      .then((data) => {
        if (isMounted && Array.isArray(data)) {
          setReviews(data)
        }
      })
      .catch((error) => {
        console.error('Error fetching reviews:', error)
      })

    return () => {
      isMounted = false
    }
  }, [user?.email, authToken])

  const refreshUserBookings = () => {
    if (!user?.email) return
    setLoading(true)
    const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {}

    fetch(
      `${API_BASE_URL}/bookings?user_email=${encodeURIComponent(user.email)}`,
      { headers }
    )
      .then((response) => response.json())
      .then((data) => {
        setBookings(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch((error) => {
        console.error('Error fetching bookings:', error)
        setLoading(false)
      })

    fetch(
      `${API_BASE_URL}/reviews?customer_email=${encodeURIComponent(user.email)}`
    )
      .then((response) => response.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setReviews(data)
        }
      })
      .catch((error) => {
        console.error('Error fetching reviews:', error)
      })
  }

  const handleCancelBooking = async (bookingId) => {
    setCancellingId(bookingId)
    setMessage('')
    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(
        `${API_BASE_URL}/bookings/${bookingId}/status`,
        {
          method: 'PATCH',
          headers,
          body: JSON.stringify({
            status: 'Rejected'
          })
        }
      )
      const data = await response.json()
      if (response.ok) {
        setMessage('Booking has been cancelled.')
        setBookings((prev) =>
          prev.map((b) => (b.id === bookingId ? { ...b, status: 'Rejected' } : b))
        )
      } else {
        setMessage(data.detail || data.message || 'Failed to cancel booking.')
      }
    } catch {
      setMessage('Network error cancelling booking.')
    } finally {
      setCancellingId(null)
    }
  }

  const handleReviewSubmit = async (booking) => {
    if (currentRating < 1 || currentRating > 5) {
      setReviewError('Please select a rating between 1 and 5 stars.')
      return
    }

    setSubmittingReview(true)
    setReviewError('')

    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(`${API_BASE_URL}/reviews`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          booking_id: booking.id,
          rating: currentRating,
          comment: reviewComment.trim()
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Review submitted successfully! Thank you for your feedback.')
        setReviews((prev) => [data, ...prev])
        setActiveRatingBookingId(null)
        setReviewComment('')
        setCurrentRating(5)
      } else {
        setReviewError(data.detail || data.message || 'Failed to submit review.')
      }
    } catch {
      setReviewError('Network error submitting review.')
    } finally {
      setSubmittingReview(false)
    }
  }

  return (
    <div className="bookings-page">
      <div className="bookings-container">
        <div className="manage-header-row">
          <div>
            <h1>My Bookings</h1>
            <p>View your current and previous service bookings.</p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="button" onClick={refreshUserBookings} className="refresh-btn">
              ↻ Refresh
            </button>
            <button type="button" onClick={onBackToDashboard}>
              Back to Dashboard
            </button>
          </div>
        </div>

        {message && (
          <div className="action-feedback-banner">
            {message}
          </div>
        )}

        {loading && <p>Loading bookings...</p>}

        {!loading && bookings.length === 0 && (
          <p>No bookings found.</p>
        )}

        <div className="bookings-list">
          {bookings.map((booking, index) => {
            const existingReview = reviews.find((r) => r.booking_id === booking.id)

            return (
              <div className="booking-card" key={booking.id || index}>
                <div className="booking-card-header">
                  <h3>{booking.service}</h3>
                  <span
                    className={`status-badge ${(booking.status || 'pending').toLowerCase()}`}
                  >
                    {booking.status}
                  </span>
                </div>

                <p>
                  <strong>Provider:</strong> {booking.provider}
                </p>

                <p>
                  <strong>Date:</strong> {booking.date}
                </p>

                <p>
                  <strong>Problem:</strong> {booking.description}
                </p>

                <p>
                  <strong>Status:</strong>{' '}
                  <span
                    className={`status-badge ${(booking.status || 'pending').toLowerCase()}`}
                  >
                    {booking.status}
                  </span>
                </p>

                {booking.status === 'Pending' && (
                  <div style={{ marginTop: '14px' }}>
                    <button
                      type="button"
                      disabled={cancellingId === booking.id}
                      onClick={() => handleCancelBooking(booking.id)}
                      className="status-btn status-btn-reject"
                    >
                      {cancellingId === booking.id ? 'Cancelling...' : 'Cancel Request'}
                    </button>
                  </div>
                )}

                {/* Rating & Review for Completed Bookings */}
                {booking.status === 'Completed' && (
                  <div className="booking-completed-feedback-area">
                    {existingReview ? (
                      <div className="booking-review-display">
                        <div className="review-display-top">
                          <span className="review-display-stars">
                            {'★'.repeat(existingReview.rating)}
                            {'☆'.repeat(5 - existingReview.rating)}
                          </span>
                          <span className="review-display-score">
                            {existingReview.rating}/5
                          </span>
                          <span className="review-submitted-badge">✓ Your Review</span>
                        </div>
                        {existingReview.comment && (
                          <p className="review-display-comment">&ldquo;{existingReview.comment}&rdquo;</p>
                        )}
                      </div>
                    ) : activeRatingBookingId === booking.id ? (
                      <div className="booking-review-form">
                        <h4>Rate &amp; Review Your Service</h4>
                        <div className="star-rating-selector">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              className={`star-btn ${star <= (hoverRating || currentRating) ? 'active' : ''}`}
                              onMouseEnter={() => setHoverRating(star)}
                              onMouseLeave={() => setHoverRating(0)}
                              onClick={() => setCurrentRating(star)}
                              title={`${star} Star${star > 1 ? 's' : ''}`}
                            >
                              ★
                            </button>
                          ))}
                          <span className="rating-desc-label">
                            {ratingLabels[hoverRating || currentRating] || 'Select rating'}
                          </span>
                        </div>
                        <textarea
                          placeholder="Write an optional review about the service and professional..."
                          value={reviewComment}
                          onChange={(e) => setReviewComment(e.target.value)}
                          rows={3}
                        />
                        {reviewError && (
                          <p className="review-error-text">{reviewError}</p>
                        )}
                        <div className="review-form-buttons">
                          <button
                            type="button"
                            className="review-cancel-btn"
                            onClick={() => {
                              setActiveRatingBookingId(null)
                              setReviewComment('')
                              setReviewError('')
                            }}
                            disabled={submittingReview}
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            className="review-submit-btn"
                            onClick={() => handleReviewSubmit(booking)}
                            disabled={submittingReview}
                          >
                            {submittingReview ? 'Submitting...' : 'Submit Review'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="rate-service-cta">
                        <button
                          type="button"
                          className="rate-service-btn"
                          onClick={() => {
                            setActiveRatingBookingId(booking.id)
                            setCurrentRating(5)
                            setHoverRating(0)
                            setReviewComment('')
                            setReviewError('')
                          }}
                        >
                          ★ Rate &amp; Review Service
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default MyBookings