import './App.css'
import { useEffect, useState } from 'react'
import Navbar from './components/Navbar'
import ServiceCard from './components/ServiceCard'
import Footer from './components/Footer'
import ProviderCard from './components/ProviderCard'
import ProviderProfile from './components/ProviderProfile'
import Register from './components/Register'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import Booking from './components/Booking'
import MyBookings from './components/MyBookings'
import ManageBookings from './components/ManageBookings'
import Profile from './components/Profile'
import FilterBar from './components/FilterBar'
import { API_BASE_URL } from './config'

function App() {
  const [services, setServices] = useState([])
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [currentPage, setCurrentPage] = useState(() => {
    const savedUser = localStorage.getItem('user')

    return savedUser ? 'dashboard' : 'home'
  })
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user')

    return savedUser ? JSON.parse(savedUser) : null
  })
  const [token, setToken] = useState(() => {
    return localStorage.getItem('token') || null
  })

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [selectedLocation, setSelectedLocation] = useState('All')
  const [sortBy, setSortBy] = useState('default')

  const categoriesList = [
    'Plumber',
    'Electrician',
    'Carpenter',
    'AC Repair',
    'Cleaning',
    'Appliance Repair'
  ]

  const availableLocations = Array.from(
    new Set(providers.map((p) => p.location).filter(Boolean))
  )

  const parseExperienceYears = (exp) => {
    if (typeof exp === 'number') return exp
    if (!exp) return 0
    const match = String(exp).match(/(\d+(\.\d+)?)/)
    return match ? parseFloat(match[1]) : 0
  }

  const handleResetFilters = () => {
    setSearchQuery('')
    setSelectedCategory('All')
    setSelectedLocation('All')
    setSortBy('default')
  }

  const hasActiveFilters = Boolean(
    searchQuery.trim() ||
    selectedCategory !== 'All' ||
    selectedLocation !== 'All' ||
    sortBy !== 'default'
  )

  const filteredServices = services.filter((service) => {
    if (
      selectedCategory !== 'All' &&
      service.name?.toLowerCase() !== selectedCategory.toLowerCase()
    ) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      const matchesName = service.name?.toLowerCase().includes(q)
      const matchesDesc = service.description?.toLowerCase().includes(q)
      if (!matchesName && !matchesDesc) {
        return false
      }
    }
    return true
  })

  const filteredProviders = providers
    .filter((provider) => {
      if (
        selectedCategory !== 'All' &&
        provider.service?.toLowerCase() !== selectedCategory.toLowerCase()
      ) {
        return false
      }
      if (
        selectedLocation !== 'All' &&
        provider.location?.toLowerCase() !== selectedLocation.toLowerCase()
      ) {
        return false
      }
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase()
        const matchesName = provider.name?.toLowerCase().includes(q)
        const matchesService = provider.service?.toLowerCase().includes(q)
        const matchesLocation = provider.location?.toLowerCase().includes(q)
        if (!matchesName && !matchesService && !matchesLocation) {
          return false
        }
      }
      return true
    })
    .sort((a, b) => {
      if (sortBy === 'rating_desc') {
        return (b.rating || 0) - (a.rating || 0)
      }
      if (sortBy === 'rating_asc') {
        return (a.rating || 0) - (b.rating || 0)
      }
      if (sortBy === 'experience_desc') {
        return parseExperienceYears(b.experience) - parseExperienceYears(a.experience)
      }
      if (sortBy === 'experience_asc') {
        return parseExperienceYears(a.experience) - parseExperienceYears(b.experience)
      }
      return 0
    })

  useEffect(() => {
    fetch(`${API_BASE_URL}/services`)
      .then(response => response.json())
      .then(data => {
        setServices(data)
      })
      .catch(error => {
        console.error('Error fetching services:', error)
      })

    fetch(`${API_BASE_URL}/providers`)
      .then(response => response.json())
      .then(data => {
        setProviders(data)
      })
      .catch(error => {
        console.error('Error fetching providers:', error)
      })
  }, [])

  return (
    <div className="app">

      <Navbar
        currentPage={currentPage}
        onLogin={() => setCurrentPage('login')}
        onRegister={() => setCurrentPage('register')}
        user={user}
        onLogout={() => {
          localStorage.removeItem('user')
          localStorage.removeItem('token')
          setUser(null)
          setToken(null)
          setCurrentPage('home')
        }}
        onDashboard={() => setCurrentPage('dashboard')}
        onHome={() => setCurrentPage('home')}
      />

      {currentPage === 'login' && (
        <Login
          onLogin={(data) => {
            setUser({
              name: data.name,
              email: data.email,
              role: data.role || 'customer',
              provider_name: data.provider_name || null
            })
            setToken(data.access_token)
            setCurrentPage('dashboard')
          }}
        />
      )}

      {currentPage === 'register' && (
        <Register
          onRegisterSuccess={() => setCurrentPage('login')}
        />
      )}

      {currentPage === 'dashboard' && (
        <Dashboard
          user={user}
          onBookService={() => setCurrentPage('home')}
          onViewBookings={() => setCurrentPage('my-bookings')}
          onManageBookings={() => setCurrentPage('manage-bookings')}
          onProfile={() => setCurrentPage('profile')}
        />
      )}

      {currentPage === 'profile' && (
        <Profile
          user={user}
          token={token}
          onBack={() => setCurrentPage('dashboard')}
          onUpdateUser={(updatedData) => {
            const updatedUser = { ...user, ...updatedData }
            setUser(updatedUser)
            localStorage.setItem('user', JSON.stringify(updatedUser))
          }}
        />
      )}

      {currentPage === 'manage-bookings' && (
        <ManageBookings
          user={user}
          token={token}
          initialProvider={selectedProvider}
          onBack={() => {
            if (user) {
              setCurrentPage('dashboard')
            } else if (selectedProvider) {
              setCurrentPage('provider-profile')
            } else {
              setCurrentPage('home')
            }
          }}
        />
      )}

      {currentPage === 'my-bookings' && (
        <MyBookings
          user={user}
          token={token}
          onBackToDashboard={() => setCurrentPage('dashboard')}
        />
      )}

      {currentPage === 'booking' && (
        <Booking
          user={user}
          token={token}
          provider={selectedProvider}
          onBack={() => {
            if (selectedProvider) {
              setCurrentPage('provider-profile')
            } else if (user) {
              setCurrentPage('dashboard')
            } else {
              setCurrentPage('home')
            }
          }}
          onBookingSuccess={() => setCurrentPage('dashboard')}
        />
      )}

{currentPage === 'provider-profile' && (
  <ProviderProfile
    provider={selectedProvider}
    user={user}
    onBack={() => setCurrentPage('home')}
    onBookNow={() => {
      setCurrentPage('booking')
    }}
    onManageBookings={(p) => {
      setSelectedProvider(p)
      setCurrentPage('manage-bookings')
    }}
    onDashboard={() => setCurrentPage('dashboard')}
  />
)}

{currentPage === 'home' && (
    

      
        <>
          {/* Hero Section */}
          <section className="hero-section">
            <div className="hero-content">
              <p className="hero-small-text">
                LOCAL SERVICES, MADE EASY
              </p>

              <h1>
                Find Trusted Local
                <span> Service Professionals</span>
              </h1>

              <p className="hero-description">
                Connect with skilled local professionals for repairs,
                maintenance and everyday services.
              </p>

              <div className="search-box">
                <input
                  type="text"
                  placeholder="Search service, provider, or location..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      document.getElementById('marketplace-controls')?.scrollIntoView({ behavior: 'smooth' })
                    }
                  }}
                />

                {searchQuery && (
                  <button
                    type="button"
                    className="hero-clear-search-btn"
                    onClick={() => setSearchQuery('')}
                    title="Clear search"
                  >
                    ✕
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => {
                    document.getElementById('marketplace-controls')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                >
                  Search
                </button>
              </div>

              {user && (
                <div className="hero-dashboard-banner">
                  <button
                    type="button"
                    className="hero-dashboard-btn"
                    onClick={() => setCurrentPage('dashboard')}
                  >
                    ← Back to Dashboard
                  </button>
                </div>
              )}
            </div>
          </section>

          {/* Marketplace Filter Controls */}
          <section id="marketplace-controls" className="marketplace-filter-section">
            <FilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              selectedCategory={selectedCategory}
              onCategoryChange={setSelectedCategory}
              categories={categoriesList}
              selectedLocation={selectedLocation}
              onLocationChange={setSelectedLocation}
              locations={availableLocations}
              sortBy={sortBy}
              onSortChange={setSortBy}
              onResetFilters={handleResetFilters}
              hasActiveFilters={hasActiveFilters}
              matchingProvidersCount={filteredProviders.length}
              matchingServicesCount={filteredServices.length}
            />
          </section>

          {/* Services Section */}
          <section id="services" className="services-section">
            <div className="section-heading">
              <p>POPULAR SERVICES</p>
              <h2>What do you need help with?</h2>
            </div>

            {filteredServices.length === 0 ? (
              <div className="no-results-card">
                <div className="no-results-icon">🔍</div>
                <h3>No services found</h3>
                <p>We couldn't find any services matching your search or selected category.</p>
                <button
                  type="button"
                  className="reset-filter-btn"
                  onClick={handleResetFilters}
                >
                  Reset All Filters
                </button>
              </div>
            ) : (
              <div className="services-grid">
                {filteredServices.map(service => (
                  <ServiceCard
                    key={service.id}
                    icon={
                      service.name === 'Plumber' ? '🔧' :
                      service.name === 'Electrician' ? '⚡' :
                      service.name === 'Carpenter' ? '🪚' :
                      service.name === 'AC Repair' ? '❄️' :
                      service.name === 'Cleaning' ? '🧹' :
                      '🔌'
                    }
                    title={service.name}
                    description={service.description}
                    isSelected={selectedCategory === service.name}
                    onClick={() => {
                      const newCat = selectedCategory === service.name ? 'All' : service.name
                      setSelectedCategory(newCat)
                      document.getElementById('providers')?.scrollIntoView({ behavior: 'smooth' })
                    }}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Providers Section */}
          <section id="providers" className="providers-section">
            <div className="section-heading">
              <p>TRUSTED PROFESSIONALS</p>
              <h2>Find the right professional for you</h2>
            </div>

            {filteredProviders.length === 0 ? (
              <div className="no-results-card">
                <div className="no-results-icon">👷</div>
                <h3>No service providers found</h3>
                <p>No providers match your current search and filter selections. Try adjusting your search keywords, category, or location filter.</p>
                <button
                  type="button"
                  className="reset-filter-btn"
                  onClick={handleResetFilters}
                >
                  Reset All Filters
                </button>
              </div>
            ) : (
              <div className="providers-grid">
                {filteredProviders.map(provider => (
                  <ProviderCard
                    key={provider.id}
                    name={provider.name}
                    service={provider.service}
                    rating={provider.rating}
                    experience={provider.experience}
                    location={provider.location}
                    onViewProfile={() => {
                      setSelectedProvider(provider)
                      setCurrentPage('provider-profile')
                    }}
                  />
                ))}
              </div>
            )}
          </section>

          {/* How It Works */}
          <section id="how-it-works" className="how-section">
            <div className="section-heading">
              <p>HOW IT WORKS</p>
              <h2>Get your service in 3 simple steps</h2>
            </div>

            <div className="steps">
              <div className="step">
                <div className="step-number">1</div>
                <h3>Choose a Service</h3>
                <p>
                  Select the service you need from our marketplace.
                </p>
              </div>

              <div className="step">
                <div className="step-number">2</div>
                <h3>Find a Professional</h3>
                <p>
                  Compare local professionals, ratings and experience.
                </p>
              </div>

              <div className="step">
                <div className="step-number">3</div>
                <h3>Book the Service</h3>
                <p>
                  Choose a suitable professional and book your service.
                </p>
              </div>
            </div>
          </section>

          <Footer />
        </>
      )}

    </div>
  )
}

export default App