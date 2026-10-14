
import { useState, useRef, useEffect } from 'react'
import { API_BASE_URL } from '../config'

function Booking({ user, token, provider, onBack, onBookingSuccess }) {
  const [userEmail, setUserEmail] = useState(user?.email || '')
  const [service, setService] = useState(provider?.service || '')
  const [providerName, setProviderName] = useState(provider?.name || '')
  const [date, setDate] = useState('')
  const [description, setDescription] = useState('')
  const [message, setMessage] = useState('')
  const [isSuccess, setIsSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const redirectTimerRef = useRef(null)

  const authToken = token || localStorage.getItem('token')

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) {
        clearTimeout(redirectTimerRef.current)
      }
    }
  }, [])

  const handleBooking = async (e) => {
    e.preventDefault()

    if (isSubmitting) return

    const emailToSend = user?.email || userEmail

    if (!emailToSend) {
      setMessage('Please enter an email address')
      setIsSuccess(false)
      return
    }

    setIsSubmitting(true)
    setMessage('')

    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(`${API_BASE_URL}/bookings`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          user_email: emailToSend,
          service,
          provider: providerName,
          date,
          description
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Booking created successfully! Redirecting to Dashboard…')
        setIsSuccess(true)
        setDate('')
        setDescription('')
        if (!user?.email) {
          setUserEmail('')
        }
        redirectTimerRef.current = setTimeout(() => {
          if (onBookingSuccess) {
            onBookingSuccess()
          }
        }, 1500)
      } else {
        setMessage(data.message || 'Booking failed')
        setIsSuccess(false)
        setIsSubmitting(false)
      }
    } catch {
      setMessage('Booking failed')
      setIsSuccess(false)
      setIsSubmitting(false)
    }
  }

  return (
    <div className="booking-page">
      <div className="booking-box">
        <h2>Book a Service</h2>
        <p>Choose a service and trusted professional.</p>

        <form onSubmit={handleBooking}>
          {!user?.email ? (
            <input
              type="email"
              placeholder="Your Email"
              value={userEmail}
              onChange={(e) => setUserEmail(e.target.value)}
              disabled={isSubmitting}
              required
            />
          ) : (
            <input
              type="email"
              value={user.email}
              disabled
              title="Logged in user email"
            />
          )}

          <input
            type="text"
            placeholder="Service"
            value={service}
            onChange={(e) => setService(e.target.value)}
            disabled={isSubmitting}
            required
          />

          <input
            type="text"
            placeholder="Provider"
            value={providerName}
            onChange={(e) => setProviderName(e.target.value)}
            disabled={isSubmitting}
            required
          />

          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            disabled={isSubmitting}
            required
          />

          <textarea
            placeholder="Describe your problem"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isSubmitting}
            required
          />

          <div style={{ display: 'flex', gap: '10px' }}>
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                disabled={isSubmitting}
                style={{ background: '#64748b', flex: 1, opacity: isSubmitting ? 0.7 : 1, cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
              >
                Back
              </button>
            )}
            <button
              type="submit"
              disabled={isSubmitting}
              style={{ flex: 1, opacity: isSubmitting ? 0.7 : 1, cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
            >
              {isSubmitting ? 'Confirming...' : 'Confirm Booking'}
            </button>
          </div>
        </form>

        {message && (
          <p
            style={{
              marginTop: '15px',
              textAlign: 'center',
              fontWeight: '500',
              color: isSuccess ? '#16a34a' : '#dc2626'
            }}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  )
}

export default Booking
