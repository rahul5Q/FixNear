function Navbar({ onLogin, onRegister, user, onLogout, onDashboard, onHome, currentPage }) {
  return (
    <nav className="navbar">
      <div
        className="logo"
        onClick={onHome}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            if (onHome) onHome()
          }
        }}
        style={{ cursor: 'pointer' }}
        title="Go to Homepage"
      >
        FixNear
      </div>

      <div className="nav-links">
        <a
          href="#services"
          onClick={() => {
            if (onHome) onHome()
          }}
        >
          Services
        </a>
        <a
          href="#providers"
          onClick={() => {
            if (onHome) onHome()
          }}
        >
          Providers
        </a>
        <a
          href="#how-it-works"
          onClick={() => {
            if (onHome) onHome()
          }}
        >
          How It Works
        </a>

        {!user ? (
          <>
            <button type="button" className="login-btn" onClick={onLogin}>
              Login
            </button>

            <button type="button" className="register-btn" onClick={onRegister}>
              Register
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className={`dashboard-nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
              onClick={onDashboard}
            >
              Dashboard
            </button>

            <span className="welcome-user">
              Hi, {user.name}
            </span>

            <button type="button" className="login-btn" onClick={onLogout}>
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  )
}

export default Navbar