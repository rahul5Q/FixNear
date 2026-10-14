import { useState } from 'react'
import { API_BASE_URL } from '../config'

function Register({ onRegisterSuccess }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('customer')
  const [providerName, setProviderName] = useState('')
  const [providerInviteCode, setProviderInviteCode] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const handleRegister = async (e) => {
    e.preventDefault()

    const cleanName = name.trim()
    const cleanEmail = email.trim()
    const cleanProviderName = providerName.trim()
    const cleanInviteCode = providerInviteCode.trim()

    if (cleanName.length < 2) {
      setMessage('Name must be at least 2 characters long.')
      setIsError(true)
      return
    }

    if (password.length < 6) {
      setMessage('Password must be at least 6 characters long.')
      setIsError(true)
      return
    }

    if (role === 'provider') {
      if (cleanProviderName.length < 2) {
        setMessage('Provider business name must be at least 2 characters long.')
        setIsError(true)
        return
      }
      if (!cleanInviteCode) {
        setMessage('Provider authorization invite code is required.')
        setIsError(true)
        return
      }
    }

    try {
      const payload = {
        name: cleanName,
        email: cleanEmail,
        password,
        role
      }
      if (role === 'provider') {
        payload.provider_name = cleanProviderName
        payload.provider_invite_code = cleanInviteCode
      }

      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage(data.message || 'Registration successful! You can now log in.')
        setIsError(false)
        setName('')
        setEmail('')
        setPassword('')
        setProviderName('')
        setProviderInviteCode('')
        setRole('customer')
        if (onRegisterSuccess) {
          setTimeout(() => {
            onRegisterSuccess()
          }, 1500)
        }
      } else {
        setMessage(data.detail || data.message || 'Registration failed')
        setIsError(true)
      }
    } catch {
      setMessage('Network error during registration. Please try again.')
      setIsError(true)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-box">
        <h2>Create Account</h2>
        <p>Register to use FixNear</p>

        <form onSubmit={handleRegister}>
          <div style={{ textAlign: 'left', marginBottom: '12px' }}>
            <label
              htmlFor="register-role"
              style={{ fontSize: '0.85rem', color: '#64748b', display: 'block', marginBottom: '4px', fontWeight: '500' }}
            >
              Account Type:
            </label>
            <select
              id="register-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '0.95rem'
              }}
            >
              <option value="customer">Customer (Book Services)</option>
              <option value="provider">Service Provider (Offer Services)</option>
            </select>
          </div>

          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          {role === 'provider' && (
            <>
              <input
                type="text"
                placeholder="Business / Provider Name (e.g. Acme Electric)"
                value={providerName}
                onChange={(e) => setProviderName(e.target.value)}
                required
                minLength={2}
                maxLength={100}
              />
              <input
                type="password"
                placeholder="Provider Authorization Invite Code"
                value={providerInviteCode}
                onChange={(e) => setProviderInviteCode(e.target.value)}
                required
              />
              <span style={{ fontSize: '0.78rem', color: '#64748b', display: 'block', textAlign: 'left', marginTop: '-8px', marginBottom: '12px' }}>
                Provider accounts require an authorization invite code from FixNear administration.
              </span>
            </>
          )}

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password (min 6 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">
            Register
          </button>
        </form>

        {message && (
          <p style={{ marginTop: '15px', color: isError ? '#dc2626' : '#16a34a', fontWeight: '500' }}>
            {message}
          </p>
        )}
      </div>
    </div>
  )
}

export default Register