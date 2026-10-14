import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../config'

function ManageBookings({ user, token, onBack, initialProvider }) {
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(
    user?.provider_name || initialProvider?.name || 'All'
  )
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionMessage, setActionMessage] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  const authToken = token || localStorage.getItem('token')

  useEffect(() => {
    fetch(`${API_BASE_URL}/providers`)
      .then((res) => res.json())
      .then((data) => setProviders(data))
      .catch((err) => console.error('Error fetching providers:', err))
  }, [])

  useEffect(() => {
    let isMounted = true

    if (!user || user.role !== 'provider' || !authToken) {
      return
    }

    const providerFilter = user.provider_name || (selectedProvider === 'All' ? '' : selectedProvider)
    const url = providerFilter
      ? `${API_BASE_URL}/bookings?provider=${encodeURIComponent(providerFilter)}`
      : `${API_BASE_URL}/bookings`

    const headers = {
      'Authorization': `Bearer ${authToken}`
    }

    fetch(url, { headers })
      .then((res) => res.json())
      .then((data) => {
        if (isMounted) {
          setBookings(Array.isArray(data) ? data : [])
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
  }, [selectedProvider, user, authToken])

  const refreshBookings = () => {
    if (!user || user.role !== 'provider' || !authToken) return
    setLoading(true)

    const providerFilter = user.provider_name || (selectedProvider === 'All' ? '' : selectedProvider)
    const url = providerFilter
      ? `${API_BASE_URL}/bookings?provider=${encodeURIComponent(providerFilter)}`
      : `${API_BASE_URL}/bookings`

    const headers = {
      'Authorization': `Bearer ${authToken}`
    }

    fetch(url, { headers })
      .then((res) => res.json())
      .then((data) => {
        setBookings(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching bookings:', err)
        setLoading(false)
      })
  }

  const handleUpdateStatus = async (bookingId, newStatus) => {
    setUpdatingId(bookingId)
    setActionMessage('')

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
            status: newStatus
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

  if (!user || user.role !== 'provider') {
    return (
      <div className="bookings-page">
        <div className="bookings-container" style={{ textAlign: 'center', padding: '50px 20px' }}>
          <h2>Provider Access Required</h2>
          <p style={{ marginTop: '12px', color: '#64748b' }}>
            Only authenticated service providers can access the Booking Management portal.
          </p>
          <p style={{ marginTop: '6px', color: '#64748b' }}>
            Please log in with a provider account (e.g. <code>amit@provider.fixnear.com</code>) to view and manage bookings.
          </p>
          <div style={{ marginTop: '24px', display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <button type="button" onClick={onBack}>
              Go Back
            </button>
          </div>
        </div>
      </div>
    )
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
                      handleUpdateStatus(booking.id, 'Accepted')
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
                      handleUpdateStatus(booking.id, 'Rejected')
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
                      handleUpdateStatus(booking.id, 'Completed')
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
                      handleUpdateStatus(booking.id, 'Pending')
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
