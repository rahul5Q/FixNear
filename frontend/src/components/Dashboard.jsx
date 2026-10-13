function Dashboard({ user, onBookService, onViewBookings, onManageBookings, onProfile }) {
  return (
    <div className="dashboard-page">
      <div className="dashboard-container">

        <div className="dashboard-header">
          <h1>Welcome, {user?.name}</h1>
          <p>{user?.email}</p>
        </div>

        <div className="dashboard-cards">

          <div className="dashboard-card">
            <h3>My Profile</h3>
            <p>View and manage your account information.</p>
            <button onClick={onProfile}>View Profile</button>
          </div>

          <div className="dashboard-card">
            <h3>My Bookings</h3>
            <p>View your current and previous service bookings.</p>
            <button onClick={onViewBookings}>
  View Bookings
</button>
          </div>

          <div className="dashboard-card">
            <h3>Find a Service</h3>
            <p>Find trusted professionals for your service needs.</p>
            <button onClick={onBookService}>
  Find Services
</button>
          </div>

          <div className="dashboard-card">
            <h3>Provider Portal</h3>
            <p>Manage incoming customer requests and booking statuses.</p>
            <button onClick={onManageBookings}>
  Manage Bookings
</button>
          </div>

        </div>

      </div>
    </div>
  )
}

export default Dashboard