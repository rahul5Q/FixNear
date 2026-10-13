# FixNear: Local Service Marketplace

[![FastAPI](https://img.shields.io/badge/FastAPI-0.142.2-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2.8-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.3.0-646CFF?logo=vite&logoColor=white)](https://vite.dev)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.18.2-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Author](https://img.shields.io/badge/Author-Rahul_Chatterjee-blue)](#author)

FixNear is a full-stack freelance service marketplace that connects homeowners and local customers with vetted, skilled service providers—including electricians, plumbers, carpenters, AC repair specialists, cleaners, and appliance technicians.

---

## Table of Contents

- [Problem Statement & Objectives](#problem-statement--objectives)
- [Key Implemented Features](#key-implemented-features)
- [Technology Stack](#technology-stack)
- [Project Architecture & Directory Structure](#project-architecture--directory-structure)
- [Prerequisites](#prerequisites)
- [Local Installation & Setup (Windows PowerShell)](#local-installation--setup-windows-powershell)
  - [1. MongoDB Database Setup](#1-mongodb-database-setup)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
- [Environment Configuration](#environment-configuration)
- [API Endpoints & Local URLs](#api-endpoints--local-urls)
- [Automated Testing & Verification](#automated-testing--verification)
  - [Running Backend Tests](#running-backend-tests)
  - [Running Frontend Checks](#running-frontend-checks)
- [Security Status & Future Roadmap](#security-status--future-roadmap)
  - [Current Security Architecture & Limitations](#current-security-architecture--limitations)
  - [Planned Future Improvements](#planned-future-improvements)
- [Author](#author)

---

## Problem Statement & Objectives

### The Problem
Finding trustworthy local repair specialists and artisans is often a frustrating, opaque process. Customers rely on informal recommendations, unverified paper ads, or fragmented search listings with little visibility into pricing, verified ratings, or provider availability.

### Objectives
- **Centralized Marketplace:** Provide a unified platform where customers can easily find, compare, and book verified service professionals across essential home-repair categories.
- **Transparent Quality:** Allow verified customers who completed service appointments to submit star ratings and detailed reviews, generating public aggregate provider scores.
- **Robust Booking Workflow:** Facilitate service scheduling with instant status tracking (Pending $\rightarrow$ Accepted / Rejected $\rightarrow$ Completed).
- **Responsive Experience:** Deliver an intuitive, mobile-optimized experience across desktops, tablets, and smartphones.

---

## Key Implemented Features

### 1. User Authentication & Session Security
- **Account Registration (`POST /register`):** Creates customer accounts with passwords securely hashed using `bcrypt`. Validates input bounds (name: 2–100 chars, password: 6–72 chars, RFC-compliant email regex). Prevents duplicate accounts with `HTTP 409 Conflict`.
- **User Login (`POST /login`):** Authenticates credentials with clear feedback, returning `HTTP 401 Unauthorized` on invalid username/password.
- **Email Normalization:** All emails are stripped of whitespace and converted to lowercase (`.strip().lower()`) across registration, login, bookings, profiles, and reviews to prevent duplicate accounts and missed lookups.
- **Session Management:** Stores authenticated user sessions in browser `localStorage` and reflects user status across the Navbar and Dashboard.

### 2. Customer Profile Management
- **Profile View (`GET /profile`):** Displays customer name and email. Requires ownership validation via the `X-User-Email` header.
- **Name Updates (`PUT /profile`, `PATCH /profile`):** Enables customers to update their display name (with $\ge 2$ characters validation). Email addresses remain immutable for account security.

### 3. Service & Provider Discovery
- **Multi-Field Search:** Real-time search across service names, categories, and provider locations.
- **Category Filtering:** Filter providers by trade: *Plumber*, *Electrician*, *Carpenter*, *AC Repair*, *Cleaning*, and *Appliance Repair*.
- **Sorting Options:** Sort providers dynamically by customer rating (highest first) and years of experience (ascending or descending).
- **Empty States:** Clear, styled fallback messages when no providers match active search criteria.

### 4. Service Booking Lifecycle
- **Booking Submission (`POST /bookings`):** Customers book services with date validation (`YYYY-MM-DD`) and issue description (3–1,000 characters).
- **Automatic Dashboard Redirect:** After booking confirmation, users see a success banner and are automatically redirected to the Dashboard after 1.5 seconds.
- **Customer Cancellation:** Customers can cancel their own `Pending` bookings directly from their "My Bookings" page.

### 5. Provider Portal & Status Management
- **Booking Oversight:** Providers can view all bookings assigned to their business.
- **Status Progression:** Providers can update booking status to `Accepted`, `Rejected`, or `Completed`.
- **Completed Booking Final Lock:** Once a booking status reaches `Completed`, the backend and frontend enforce a final terminal lock. Completed bookings cannot be reverted back to `Pending`, `Accepted`, or `Rejected` through either UI controls or API requests (`HTTP 400 Bad Request`).

### 6. Customer Rating and Review System
- **Completed Booking Prerequisite:** Reviews can only be submitted for bookings in `Completed` status.
- **Interactive Ratings:** Interactive 1–5 star rating with an optional written review (up to 1,000 characters).
- **Duplicate Prevention:** Prevents multiple reviews for the same booking.
- **Cross-Customer Protection:** Enforces that only the customer who booked the service can submit a review.
- **Provider Aggregate Scores:** Dynamically computes and displays the provider's average star rating and review count on the Provider Profile page.

### 7. Responsive Navigation
- **Top Navbar:** Displays direct "Dashboard" navigation button for authenticated users alongside service links, user display name, and Logout.
- **Homepage Return Link:** Prominent "Back to Dashboard" button in the hero search section for logged-in visitors.
- **Provider Profile Navigation:** Direct buttons to return to Dashboard, view provider bookings, or Book Now.

---

## Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | React | `^19.2.8` | Component-based User Interface |
| **Frontend Tooling** | Vite | `^8.3.0` | High-speed frontend build tool & dev server |
| **Styling** | Vanilla CSS3 | Standard | Custom responsive mobile/tablet/desktop styling |
| **Linting** | ESLint | `^10.10.0` | Frontend code quality and React hooks rules |
| **Backend** | Python | 3.12 | Core backend language |
| **Web Framework** | FastAPI | `0.142.2` | High-performance asynchronous REST API framework |
| **ASGI Server** | Uvicorn | `0.54.0` | Production ASGI web server |
| **Database** | MongoDB | Community Server | Document-based NoSQL database |
| **DB Driver** | PyMongo | `4.18.2` | Python driver for MongoDB |
| **Data Validation** | Pydantic | `2.13.5` | Data validation and request schemas |
| **Password Security** | Bcrypt | `5.0.0` | One-way salted password hashing |
| **Configuration** | python-dotenv | `1.2.4` | Loads environment variables from `.env` files |

---

## Project Architecture & Directory Structure

```
local-service-marketplace/
├── .env.example                     # Example root environment configuration
├── .gitignore                       # Repository-wide Git exclusions
├── README.md                        # Project documentation (this file)
│
├── backend/                         # FastAPI Application
│   ├── .env.example                 # Example backend environment configuration
│   ├── main.py                      # FastAPI routes, DB models, validation & logic
│   ├── requirements.txt             # Python package dependencies
│   ├── test_phase6a_security.py     # Authorization & ownership test suite
│   ├── test_phase6b.py              # Input validation & normalization test suite
│   ├── test_phase6c_env.py          # Git hygiene & env variable test suite
│   └── test_reviews.py              # Phase 4 reviews & ratings test suite
│
├── docs/                            # Project Documentation
│   └── PROJECT_REQUIREMENTS.md      # Detailed system requirements specification
│
└── frontend/                        # React + Vite Application
    ├── .env.example                 # Example frontend environment configuration
    ├── .gitignore                   # Frontend Git exclusions
    ├── eslint.config.js             # ESLint configuration
    ├── index.html                   # HTML entry point with viewport meta tag
    ├── package.json                 # Frontend dependencies and npm scripts
    ├── package-lock.json            # Exact dependency lockfile
    ├── README.md                    # Frontend-specific documentation
    ├── vite.config.js               # Vite build configuration
    ├── public/                      # Static assets
    │   ├── favicon.svg              # Platform favicon
    │   └── icons.svg                # Inline SVG symbol definitions
    └── src/                         # Source code
        ├── assets/                  # Hero illustrations and static images
        ├── components/              # Modular UI components
        │   ├── Booking.jsx          # Service booking form with auto-redirect
        │   ├── Dashboard.jsx        # Customer dashboard hub
        │   ├── FilterBar.jsx        # Search, category filter & sort bar
        │   ├── Footer.jsx           # Footer component
        │   ├── Login.jsx            # User login component with status alerts
        │   ├── ManageBookings.jsx   # Provider portal booking status controls
        │   ├── MyBookings.jsx       # Customer booking manager & review submission
        │   ├── Navbar.jsx           # Top navigation bar
        │   ├── Profile.jsx          # Profile viewing & name editing
        │   ├── ProviderCard.jsx     # Provider summary card
        │   ├── ProviderProfile.jsx  # Detailed provider profile & reviews
        │   ├── Register.jsx         # User registration with status alerts
        │   └── ServiceCard.jsx      # Service category card
        ├── App.css                  # Responsive styling across all viewports
        ├── App.jsx                  # Main view router & state management
        ├── config.js                # Central API configuration (VITE_API_URL)
        ├── index.css                # Global CSS reset
        └── main.jsx                 # React root mount point
```

---

## Prerequisites

Before running the application locally, ensure you have the following installed on Windows:

1. **Python 3.10+** (Python 3.12 recommended). Ensure `python` or `py` is available.
2. **Node.js 18+** with `npm` (Node.js 20+ LTS recommended).
3. **MongoDB Community Server** installed and running as a service on port `27017`.
4. **Git** (for version control).
5. **Windows PowerShell 5.1** or **PowerShell 7+**.

---

## Local Installation & Setup (Windows PowerShell)

### 1. MongoDB Database Setup

Ensure your local MongoDB service is running:

```powershell
# Check if the MongoDB Windows service is running
Get-Service -Name MongoDB

# If stopped, start the service
Start-Service -Name MongoDB
```

The database `local_service_marketplace` and initial seed data for `services` and `providers` will be initialized automatically by `backend/main.py` upon first launch.

---

### 2. Backend Setup

Open a PowerShell terminal and navigate to the project root:

```powershell
# 1. Change to the backend directory
cd backend

# 2. Create a virtual environment (if not already created)
python -m venv venv

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install backend dependencies
pip install -r requirements.txt

# 5. (Optional) Set up your environment file
Copy-Item .env.example .env

# 6. Start the FastAPI development server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend server will start at: **`http://127.0.0.1:8000`**  
Interactive API Documentation will be available at: **`http://127.0.0.1:8000/docs`**

---

### 3. Frontend Setup

Open a **separate** PowerShell terminal and navigate to the project root:

```powershell
# 1. Change to the frontend directory
cd frontend

# 2. Install npm dependencies
npm install

# 3. (Optional) Set up your environment file
Copy-Item .env.example .env

# 4. Start the Vite development server
npm run dev
```

The React frontend will start at: **`http://localhost:5173/`**

---

## Environment Configuration

FixNear uses environment variables with safe offline fallbacks for local development.

### Backend (`backend/.env` or project root `.env`)

```env
# MongoDB Connection URI (defaults to mongodb://localhost:27017/ if unset)
MONGO_URI=mongodb://localhost:27017/
```

- Loaded via `python-dotenv` in `backend/main.py`.
- If `MONGO_URI` is omitted, the backend defaults to `mongodb://localhost:27017/`.

### Frontend (`frontend/.env` or project root `.env`)

```env
# API Base URL (defaults to http://127.0.0.1:8000 if unset)
VITE_API_URL=http://127.0.0.1:8000
```

- Configured in `frontend/src/config.js` via `import.meta.env.VITE_API_URL`.
- Automatically strips any trailing slash.
- If `VITE_API_URL` is omitted, the frontend defaults to `http://127.0.0.1:8000`.

---

## API Endpoints & Local URLs

### Local Access URLs

- **Frontend Application:** `http://localhost:5173/`
- **Backend API Base:** `http://127.0.0.1:8000/`
- **Swagger Interactive API Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc API Documentation:** `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`

### Key REST Endpoints

| Method | Endpoint | Description | Auth / Security Header |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API status and welcome message | Public |
| `GET` | `/db-test` | MongoDB connection verification | Public |
| `GET` | `/services` | List all 6 service categories | Public |
| `GET` | `/providers` | List all service providers | Public |
| `POST` | `/register` | Register new customer account | Public (Password hashed via bcrypt) |
| `POST` | `/login` | Authenticate existing user | Public (Returns 401 on bad credentials) |
| `GET` | `/profile?email=...` | Retrieve customer profile | `X-User-Email` (must match query email) |
| `PUT` | `/profile` | Update customer display name | `X-User-Email` (email cannot be altered) |
| `POST` | `/bookings` | Create a new service booking | Public / User email validated |
| `GET` | `/bookings` | Query bookings (customer or provider view) | `X-User-Email` (customer) or `X-Role: provider` |
| `GET` | `/bookings/{id}` | Retrieve individual booking details | Public |
| `PATCH`| `/bookings/{id}/status` | Update booking status (`Accepted`/`Rejected`/`Completed`) | `X-Role: provider` or `X-User-Email` (customer cancel) |
| `POST` | `/reviews` | Submit rating & review for completed booking | `X-User-Email` (must match booking customer) |
| `GET` | `/reviews` | Retrieve reviews filtered by provider or email | Public |
| `GET` | `/reviews/summary` | Aggregate provider rating score and count | Public |

---

## Automated Testing & Verification

FixNear contains a comprehensive suite of automated tests for security, input validation, environment handling, and reviews.

### Running Backend Tests

Run all tests from the repository root using the virtual environment Python:

```powershell
# 1. Phase 6A: Critical Authorization & Ownership Security Tests
& ".\backend\venv\Scripts\python.exe" -c "
import subprocess, time, sys, urllib.request
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], cwd='backend')
try:
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/db-test', timeout=1) as r:
                if r.status == 200: break
        except Exception: time.sleep(0.3)
    sys.path.insert(0, 'backend')
    import test_phase6a_security
    test_phase6a_security.run_tests()
finally:
    proc.terminate()
"

# 2. Phase 6B: Data Validation, Email Normalization & HTTP Codes Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase6b.py

# 3. Phase 6C: Git Hygiene, Environment Variables & Config Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase6c_env.py

# 4. Phase 4: Customer Rating & Review System Tests
& ".\backend\venv\Scripts\python.exe" -c "
import subprocess, time, sys, urllib.request
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], cwd='backend')
try:
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/db-test', timeout=1) as r:
                if r.status == 200: break
        except Exception: time.sleep(0.3)
    sys.path.insert(0, 'backend')
    import test_reviews
    test_reviews.run_tests()
finally:
    proc.terminate()
"
```

All test suites automatically clean up test documents and verify MongoDB collections integrity upon completion.

### Running Frontend Checks

From the `frontend/` directory:

```powershell
cd frontend

# Run ESLint check
npm run lint

# Run production build check
npm run build
```

---

## Security Status & Future Roadmap

### Current Security Architecture & Limitations

1. **Client Identity Headers (`X-User-Email`, `X-Role`):**
   - *Current Implementation:* The frontend passes `X-User-Email` and `X-Role: provider` headers to verify resource ownership on profile and booking endpoints.
   - *Limitation:* Headers originate from the browser client without cryptographic token signatures.
   - *Recommendation:* Upgrade to signed JSON Web Tokens (JWT) or HTTP-only session cookies in production.
2. **Provider Role Verification:**
   - *Current Implementation:* Providers authenticate by supplying their registered provider name.
   - *Limitation:* Providers do not currently have distinct password-protected provider accounts.
   - *Recommendation:* Introduce dedicated provider authentication with separate login credentials.
3. **CORS Policy:**
   - *Current Implementation:* Backend CORS restricts origins to local dev URLs: `http://localhost:5173` and `http://127.0.0.1:5173`.
   - *Recommendation:* Configure environment-driven `ALLOWED_ORIGINS` when deploying to production domains.

### Planned Future Improvements

- **AI/ML Service Classification:** Automatically analyze customer problem descriptions (e.g., *"Water dripping under kitchen sink"*) and classify them into the appropriate service category (*Plumbing*).
- **AI/ML Provider Recommendation:** Smart ranking algorithms considering proximity, availability, rating distribution, and experience.
- **Payment Gateway Integration:** Secure online escrow and payment processing (e.g., Stripe, Razorpay).
- **Real-Time Communication:** WebSockets for live chat between customers and providers.
- **Provider KYC & Verification:** Document upload and admin verification for artisan credentials.
- **Real-Time Notifications:** Email / SMS / Push notifications for booking status updates.

---

## Author

**Rahul Chatterjee**  
- GitHub: [@rahul5Q](https://github.com/rahul5Q)  
- Project: FixNear Local Service Marketplace
