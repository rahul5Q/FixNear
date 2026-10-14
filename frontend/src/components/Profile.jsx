import { useState, useEffect } from 'react'
import { API_BASE_URL } from '../config'

function Profile({ user, token, onBack, onUpdateUser }) {
  const [name, setName] = useState(user?.name || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const authToken = token || localStorage.getItem('token')

  useEffect(() => {
    let isMounted = true
    if (user?.email && authToken) {
      fetch(`${API_BASE_URL}/profile`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
        .then((res) => {
          if (res.status === 401) {
            throw new Error('Session expired. Please log in again.')
          }
          return res.json()
        })
        .then((data) => {
          if (isMounted && data.name) {
            setName(data.name)
          }
        })
        .catch((err) => {
          console.error('Error fetching profile:', err)
          if (isMounted && err.message.includes('Session expired')) {
            setMessage('Session expired. Please log in again.')
            setIsError(true)
          }
        })
    }
    return () => {
      isMounted = false
    }
  }, [user?.email, authToken])

  const handleUpdate = async (e) => {
    e.preventDefault()
    const trimmedName = name.trim()

    if (!trimmedName) {
      setMessage('Name cannot be empty.')
      setIsError(true)
      return
    }

    if (trimmedName.length < 2) {
      setMessage('Name must be at least 2 characters long.')
      setIsError(true)
      return
    }

    setSaving(true)
    setMessage('')
    setIsError(false)

    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          email: user?.email,
          name: trimmedName
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage('Profile updated successfully!')
        setIsError(false)
        if (onUpdateUser) {
          onUpdateUser({ name: data.name })
        }
      } else {
        setMessage(data.detail || data.message || 'Failed to update profile.')
        setIsError(true)
      }
    } catch {
      setMessage('Network error updating profile.')
      setIsError(true)
    } finally {
      setSaving(false)
    }
  }

  if (!user) {
    return (
      <div className="profile-page">
        <div className="profile-card">
          <h2>My Profile</h2>
          <p>Please log in to view and manage your profile.</p>
          <button type="button" onClick={onBack} className="back-btn">
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const initialLetter = (name || user?.name || 'U').charAt(0).toUpperCase()

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-avatar">
          {initialLetter}
        </div>

        <h2>My Profile</h2>
        <p className="profile-subtitle">View and update your FixNear personal details</p>

        <form onSubmit={handleUpdate} className="profile-form">
          <div className="profile-field">
            <label htmlFor="profile-email">Email Address</label>
            <input
              id="profile-email"
              type="email"
              value={user.email}
              disabled
              title="Email address cannot be changed"
            />
            <span className="field-hint">Email address cannot be changed.</span>
          </div>

          <div className="profile-field">
            <label htmlFor="profile-name">Full Name</label>
            <input
              id="profile-name"
              type="text"
              placeholder="Enter your full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
              maxLength={100}
            />
          </div>

          {message && (
            <div className={`action-feedback-banner ${isError ? 'feedback-error' : ''}`}>
              {message}
            </div>
          )}

          <div className="profile-actions">
            <button
              type="button"
              onClick={onBack}
              className="back-btn"
            >
              Back to Dashboard
            </button>
            <button
              type="submit"
              disabled={saving || !name.trim() || name.trim() === user.name}
              className="save-btn"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Profile
