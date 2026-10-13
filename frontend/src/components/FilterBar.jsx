function FilterBar({
  searchQuery,
  onSearchChange,
  selectedCategory,
  onCategoryChange,
  categories,
  selectedLocation,
  onLocationChange,
  locations,
  sortBy,
  onSortChange,
  onResetFilters,
  hasActiveFilters,
  matchingProvidersCount,
  matchingServicesCount
}) {
  const sortLabels = {
    default: 'Default',
    rating_desc: 'Rating: High to Low',
    rating_asc: 'Rating: Low to High',
    experience_desc: 'Experience: Most to Least',
    experience_asc: 'Experience: Least to Most'
  }

  return (
    <div className="filter-bar-container">
      <div className="filter-bar-card">
        {/* Top search & quick controls row */}
        <div className="filter-controls-row">
          {/* Search Input */}
          <div className="filter-control-group filter-search-group">
            <label htmlFor="filter-search-input">Search Marketplace</label>
            <div className="filter-input-wrapper">
              <span className="filter-icon">🔍</span>
              <input
                id="filter-search-input"
                type="text"
                placeholder="Search name, category, or location..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="filter-clear-input-btn"
                  onClick={() => onSearchChange('')}
                  title="Clear search term"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* Category Dropdown */}
          <div className="filter-control-group">
            <label htmlFor="filter-category-select">Category</label>
            <select
              id="filter-category-select"
              value={selectedCategory}
              onChange={(e) => onCategoryChange(e.target.value)}
            >
              <option value="All">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Location Dropdown */}
          <div className="filter-control-group">
            <label htmlFor="filter-location-select">Location</label>
            <select
              id="filter-location-select"
              value={selectedLocation}
              onChange={(e) => onLocationChange(e.target.value)}
            >
              <option value="All">All Locations</option>
              {locations.map((loc) => (
                <option key={loc} value={loc}>
                  {loc}
                </option>
              ))}
            </select>
          </div>

          {/* Sort By Dropdown */}
          <div className="filter-control-group">
            <label htmlFor="filter-sort-select">Sort Providers</label>
            <select
              id="filter-sort-select"
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value)}
            >
              <option value="default">Default</option>
              <option value="rating_desc">Rating: High to Low</option>
              <option value="rating_asc">Rating: Low to High</option>
              <option value="experience_desc">Experience: Most to Least</option>
              <option value="experience_asc">Experience: Least to Most</option>
            </select>
          </div>
        </div>

        {/* Quick Category Pills */}
        <div className="category-pills-row">
          <span className="pills-label">Quick Categories:</span>
          <div className="pills-list">
            <button
              type="button"
              className={`category-pill ${selectedCategory === 'All' ? 'active' : ''}`}
              onClick={() => onCategoryChange('All')}
            >
              All
            </button>
            {categories.map((cat) => (
              <button
                type="button"
                key={cat}
                className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => onCategoryChange(selectedCategory === cat ? 'All' : cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Active Filters & Results Summary */}
        <div className="filter-summary-row">
          <div className="filter-results-badge">
            Showing <strong>{matchingProvidersCount}</strong> provider{matchingProvidersCount !== 1 ? 's' : ''} &amp; <strong>{matchingServicesCount}</strong> service{matchingServicesCount !== 1 ? 's' : ''}
          </div>

          {hasActiveFilters && (
            <div className="active-filters-list">
              {searchQuery.trim() && (
                <span className="active-filter-chip">
                  Search: &ldquo;{searchQuery.trim()}&rdquo;
                  <button type="button" onClick={() => onSearchChange('')}>✕</button>
                </span>
              )}
              {selectedCategory !== 'All' && (
                <span className="active-filter-chip">
                  Category: {selectedCategory}
                  <button type="button" onClick={() => onCategoryChange('All')}>✕</button>
                </span>
              )}
              {selectedLocation !== 'All' && (
                <span className="active-filter-chip">
                  Location: {selectedLocation}
                  <button type="button" onClick={() => onLocationChange('All')}>✕</button>
                </span>
              )}
              {sortBy !== 'default' && (
                <span className="active-filter-chip">
                  Sort: {sortLabels[sortBy]}
                  <button type="button" onClick={() => onSortChange('default')}>✕</button>
                </span>
              )}
              <button
                type="button"
                className="clear-all-filters-btn"
                onClick={onResetFilters}
              >
                Clear All Filters
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FilterBar
