import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

function ManageBookings({ user, onBack, initialProvider }) {
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(
    initialProvider?.name || 'All'
  )
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionMessage, setActionMessage] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/providers`)
      .then((res) => res.json())
      .then((data) => setProviders(data))
      .catch((err) => console.error('Error fetching providers:', err))
  }, [])

  useEffect(() => {
    let isMounted = true

    const url =
      selectedProvider === 'All'
        ? `${API_BASE_URL}/bookings`
        : `${API_BASE_URL}/bookings?provider=${encodeURIComponent(selectedProvider)}`

    const headers = {
      'X-Role': 'provider',
      ...(user?.email ? { 'X-User-Email': user.email } : {})
    }

    fetch(url, { headers })
      .then((res) => res.json())
      .then((data) => {
        if (isMounted) {
          setBookings(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        console.error('Error fetching bookings:', err)
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [selectedProvider, user?.email])

  const refreshBookings = () => {
    setLoading(true)
    const url =
      selectedProvider === 'All'
        ? `${API_BASE_URL}/bookings`
        : `${API_BASE_URL}/bookings?provider=${encodeURIComponent(selectedProvider)}`

    const headers = {
      'X-Role': 'provider',
      ...(user?.email ? { 'X-User-Email': user.email } : {})
    }

    fetch(url, { headers })
      .then((res) => res.json())
      .then((data) => {
        setBookings(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching bookings:', err)
        setLoading(false)
      })
  }

  const handleUpdateStatus = async (bookingId, newStatus, providerName) => {
    setUpdatingId(bookingId)
    setActionMessage('')

    try {
      const response = await fetch(
        `${API_BASE_URL}/bookings/${bookingId}/status`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-Role': 'provider',
            ...(user?.email ? { 'X-User-Email': user.email } : {})
          },
          body: JSON.stringify({
            status: newStatus,
            role: 'provider',
            provider_name: providerName,
            updater_email: user?.email
          })
        }
      )

      const data = await response.json()

      if (response.ok) {
        setActionMessage(`Booking marked as ${newStatus}`)
        setBookings((prev) =>
          prev.map((b) => (b.id === bookingId ? { ...b, status: newStatus } : b))
        )
      } else {
        setActionMessage(data.detail || data.message || 'Failed to update status')
      }
    } catch {
      setActionMessage('Network error updating status')
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="bookings-page">
      <div className="bookings-container">
        <div className="manage-header-row">
          <div>
            <h1>Provider Booking Management</h1>
            <p>Review customer requests and update service booking statuses.</p>
          </div>
          <button onClick={onBack}>Back to Dashboard</button>
        </div>

        {/* Provider Filter */}
        <div className="provider-filter-bar">
          <label htmlFor="provider-select">
            <strong>Provider Filter:</strong>
          </label>
          <select
            id="provider-select"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
          >
            <option value="All">All Providers</option>
            {providers.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name} ({p.service})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={refreshBookings}
            className="refresh-btn"
          >
            ↻ Refresh
          </button>
        </div>

        {actionMessage && (
          <div className="action-feedback-banner">
            {actionMessage}
          </div>
        )}

        {loading && <p>Loading incoming bookings...</p>}

        {!loading && bookings.length === 0 && (
          <p>No bookings found for the selected filter.</p>
        )}

        <div className="bookings-list">
          {bookings.map((booking) => (
            <div className="booking-card" key={booking.id}>
              <div className="booking-card-header">
                <h3>{booking.service}</h3>
                <span
                  className={`status-badge ${(booking.status || 'pending').toLowerCase()}`}
                >
                  {booking.status}
                </span>
              </div>

              <p>
                <strong>Customer:</strong> {booking.user_email}
              </p>
              <p>
                <strong>Provider:</strong> {booking.provider}
              </p>
              <p>
                <strong>Date:</strong> {booking.date}
              </p>
              <p>
                <strong>Problem:</strong> {booking.description}
              </p>

              {/* Status Controls */}
              <div className="booking-status-controls">
                <span className="controls-label">
                  {booking.status === 'Completed'
                    ? 'Status: Completed (Finalized)'
                    : 'Update Status:'}
                </span>
                <div className="controls-buttons">
                  <button
                    type="button"
                    disabled={
                      updatingId === booking.id ||
                      booking.status === 'Completed' ||
                      booking.status === 'Accepted'
                    }
                    onClick={() =>
                      handleUpdateStatus(booking.id, 'Accepted', booking.provider)
                    }
                    className="status-btn status-btn-accept"
                  >
                    ✓ Accept
                  </button>

                  <button
                    type="button"
                    disabled={
                      updatingId === booking.id ||
                      booking.status === 'Completed' ||
                      booking.status === 'Rejected'
                    }
                    onClick={() =>
                      handleUpdateStatus(booking.id, 'Rejected', booking.provider)
                    }
                    className="status-btn status-btn-reject"
                  >
                    ✕ Reject
                  </button>

                  <button
                    type="button"
                    disabled={
                      updatingId === booking.id ||
                      booking.status === 'Completed'
                    }
                    onClick={() =>
                      handleUpdateStatus(booking.id, 'Completed', booking.provider)
                    }
                    className="status-btn status-btn-complete"
                  >
                    ★ Complete
                  </button>

                  <button
                    type="button"
                    disabled={
                      updatingId === booking.id ||
                      booking.status === 'Completed' ||
                      booking.status === 'Pending'
                    }
                    onClick={() =>
                      handleUpdateStatus(booking.id, 'Pending', booking.provider)
                    }
                    className="status-btn status-btn-pending"
                  >
                    ↺ Pending
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ManageBookings
