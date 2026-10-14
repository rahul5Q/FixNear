import { useState } from 'react'
import { API_BASE_URL } from '../config'

function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    const cleanEmail = email.trim()

    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: cleanEmail,
          password
        })
      })

      const data = await response.json()

      if (response.ok && data.name && data.email) {
        setMessage('Login successful!')
        setIsError(false)
        localStorage.setItem(
          'user',
          JSON.stringify({
            name: data.name,
            email: data.email,
            role: data.role || 'customer',
            provider_name: data.provider_name || null
          })
        )
        if (data.access_token) {
          localStorage.setItem('token', data.access_token)
        }
        onLogin(data)
      } else {
        setMessage(data.detail || data.message || 'Invalid email or password')
        setIsError(true)
      }
    } catch {
      setMessage('Network error during login. Please try again.')
      setIsError(true)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-box">
        <h2>Welcome Back</h2>
        <p>Login to your FixNear account</p>

        <form onSubmit={handleLogin}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit">
            Login
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

export default Login