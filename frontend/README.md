# FixNear Frontend

The client-side interface for **FixNear** (Freelance Service Marketplace for Local Repairs and Artisan Services), built with **React 19** and **Vite**.

---

## Features

- **Single Page Application (SPA):** Fast client-side routing between Home, Discovery, Dashboard, Profile, Booking, and Reviews.
- **Search & Filtering:** Real-time search across service names, categories, and provider locations with sorting by rating and experience.
- **Booking Flow:** Responsive booking request form with automatic redirection to the customer Dashboard upon confirmation.
- **Provider Portal:** Dedicated status management view for service providers to accept and complete bookings.
- **Customer Reviews:** Interactive 1–5 star ratings and reviews for completed bookings with aggregate provider scores.
- **Responsive Design:** Mobile-first layout optimized for mobile ($\le 600$px), tablet ($\le 768$px / $900$px), and desktop viewports.

---

## Technology Stack

- **Framework:** React 19 (`^19.2.8`)
- **Build Tool:** Vite (`^8.3.0`)
- **Styling:** Vanilla CSS3 (`src/App.css`, `src/index.css`)
- **Linter:** ESLint (`^10.10.0`) with React Hooks and React Refresh plugins

---

## Environment Configuration

The frontend connects to the FastAPI backend using `VITE_API_URL`.

A template is provided in `.env.example`:

```env
# Frontend Environment Configuration
# FixNear Backend API URL (defaults to http://127.0.0.1:8000 if unset)
VITE_API_URL=http://127.0.0.1:8000
```

To configure a custom backend endpoint:
```powershell
Copy-Item .env.example .env
```

If `.env` is omitted, `src/config.js` automatically falls back to `http://127.0.0.1:8000`.

---

## Getting Started (Windows PowerShell)

Ensure [Node.js](https://nodejs.org/) (v18+) is installed.

```powershell
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

The frontend will start at: `http://localhost:5173/`

---

## Available Scripts

| Command | Description |
| :--- | :--- |
| `npm run dev` | Starts the Vite dev server with Hot Module Replacement (HMR). |
| `npm run build` | Compiles and optimizes assets into the `dist/` directory for production. |
| `npm run lint` | Runs ESLint across all `.js` and `.jsx` files. |
| `npm run preview` | Serves the production build locally for testing. |

---

## Directory Structure

```
frontend/
├── public/                 # Static SVG icons and favicon
├── src/
│   ├── assets/             # Images and branding assets
│   ├── components/         # React UI components
│   │   ├── Booking.jsx         # Booking form with auto-redirect
│   │   ├── Dashboard.jsx       # Customer dashboard hub
│   │   ├── FilterBar.jsx       # Search, category filter & sorting controls
│   │   ├── Footer.jsx          # Page footer
│   │   ├── Login.jsx           # User authentication form
│   │   ├── ManageBookings.jsx  # Provider portal booking status controls
│   │   ├── MyBookings.jsx      # Customer booking management & review submission
│   │   ├── Navbar.jsx          # Header navigation with dashboard link
│   │   ├── Profile.jsx         # User profile view and name editor
│   │   ├── ProviderCard.jsx    # Provider summary card
│   │   ├── ProviderProfile.jsx # Provider profile view & review list
│   │   ├── Register.jsx        # Account registration form
│   │   └── ServiceCard.jsx     # Service category card
│   ├── App.css             # Responsive styling rules
│   ├── App.jsx             # Main application state and page router
│   ├── config.js           # Central API configuration (VITE_API_URL)
│   ├── index.css           # Global CSS resets
│   └── main.jsx            # React root mount point
├── .env.example            # Environment configuration template
├── .gitignore              # Frontend git exclusion list
├── eslint.config.js        # ESLint flat configuration
├── index.html              # HTML shell with responsive viewport meta tag
├── package.json            # Project dependencies and npm scripts
└── vite.config.js          # Vite build configuration
```
