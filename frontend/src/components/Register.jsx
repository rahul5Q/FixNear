import { useState } from 'react'
import { API_BASE_URL } from '../config'

function Register() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const handleRegister = async (e) => {
    e.preventDefault()

    const cleanName = name.trim()
    const cleanEmail = email.trim()

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

    try {
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: cleanName,
          email: cleanEmail,
          password
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage(data.message || 'Registration successful! You can now log in.')
        setIsError(false)
        setName('')
        setEmail('')
        setPassword('')
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
          <input
            type="text"
            placeholder="Full Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

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