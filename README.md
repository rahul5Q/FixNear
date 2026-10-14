# FixNear: Local Service Marketplace

[![FastAPI](https://img.shields.io/badge/FastAPI-0.142.2-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2.8-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.3.0-646CFF?logo=vite&logoColor=white)](https://vite.dev)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.18.2-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Author](https://img.shields.io/badge/Author-Rahul_Chatterjee-blue)](#author)

FixNear is a full-stack freelance service marketplace that connects homeowners and local customers with skilled service providers -- including electricians, plumbers, carpenters, AC repair specialists, cleaners, and appliance technicians.

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
  - [Safe Configuration Templates](#safe-configuration-templates)
  - [Backend Configuration Variables](#backend-configuration-variables)
  - [Frontend Configuration Variables](#frontend-configuration-variables)
- [API Endpoints & Local URLs](#api-endpoints--local-urls)
  - [Local Access URLs](#local-access-urls)
  - [REST API Endpoints](#rest-api-endpoints)
- [Automated Testing & Verification](#automated-testing--verification)
  - [Running Backend Test Suites](#running-backend-test-suites)
  - [Running Frontend Checks](#running-frontend-checks)
- [Security Architecture & Current Limitations](#security-architecture--current-limitations)
  - [Implemented Security Controls](#implemented-security-controls)
  - [Current Security Limitations](#current-security-limitations)
  - [Planned Future Improvements](#planned-future-improvements)
- [Author](#author)

---

## Problem Statement & Objectives

### The Problem
Finding dependable local repair specialists and artisans is often a frustrating, fragmented process. Customers rely on informal word-of-mouth recommendations, unverified paper flyers, or directory listings with little visibility into pricing, verified ratings, or provider availability.

### Objectives
- **Centralized Marketplace:** Provide a unified platform where customers can easily search, filter, compare, and book service professionals across essential repair and home-maintenance categories.
- **Transparent Feedback:** Allow verified customers who completed service appointments to submit star ratings and detailed reviews, generating public aggregate provider scores.
- **Robust Booking Lifecycle:** Facilitate service scheduling with instant status tracking (`Pending` -> `Accepted` / `Rejected` -> `Completed`).
- **Cryptographic Authentication & Authorization:** Secure user profiles, bookings, and provider management using signed JSON Web Tokens (JWT) with strict server-side role and ownership verification.
- **Responsive Experience:** Deliver an intuitive, mobile-optimized experience across desktop, tablet, and mobile viewports.

---

## Key Implemented Features

### 1. User Authentication & Session Management
- **Account Registration (`POST /register`):** Creates customer accounts with passwords securely hashed using `bcrypt`. Validates input boundaries (name: 2-100 characters, password: 6-72 characters, RFC-compliant email regex). Prevents duplicate registrations with `HTTP 409 Conflict`.
- **Provider Registration Control:** Provider registration requires an administrative authorization code (`provider_invite_code`) matching `PROVIDER_INVITE_SECRET` (`HTTP 403 Forbidden` if omitted or invalid).
- **User Login (`POST /login`):** Authenticates credentials with clear feedback, returning `HTTP 401 Unauthorized` on invalid username/password.
- **Signed JWT Access Tokens:** Issues signed `PyJWT` access tokens using the `HS256` algorithm. Each token encodes standard `sub` (email), `iat` (issued-at timestamp), and `exp` (expiration timestamp, configurable via `JWT_EXPIRE_MINUTES`, default 24 hours).
- **Server-Derived Identity:** Identity and roles (`customer`, `provider`, `admin`) are resolved strictly server-side from the verified JWT payload and database records. The backend never accepts client-asserted identity or role headers.
- **Email Normalization:** All emails are stripped of leading/trailing whitespace and converted to lowercase (`.strip().lower()`) across registration, login, bookings, profiles, and reviews.
- **Session Management:** Stores authenticated user sessions in browser `localStorage` and clears the token upon user logout.

### 2. Rate Limiting & Abuse Prevention
- **IP-Based Throttling:** Protects `/login` and `/register` endpoints against brute-force attacks using `SlowAPI` (built on the `limits` engine).
- **Configurable Thresholds:** Configured via `LOGIN_RATE_LIMIT` (default: `10/minute` in production, `60/minute` in development) and `REGISTER_RATE_LIMIT` (default: `5/minute` in production, `60/minute` in development).
- **HTTP 429 Status:** When thresholds are exceeded, the API returns `HTTP 429 Too Many Requests` with a descriptive message.

### 3. Customer Profile Management
- **Profile View (`GET /profile`):** Displays customer account details. Requires `Authorization: Bearer <token>` and enforces ownership checks to prevent cross-user profile inspection (`HTTP 403 Forbidden`).
- **Name Updates (`PUT /profile`, `PATCH /profile`):** Enables customers to update their display name (with >= 2 character validation). Email addresses remain immutable.

### 4. Service & Provider Discovery
- **Multi-Field Search:** Real-time search across service names, categories, and provider locations.
- **Category Filtering:** Filter providers by trade: *Plumber*, *Electrician*, *Carpenter*, *AC Repair*, *Cleaning*, and *Appliance Repair*.
- **Sorting Options:** Sort providers dynamically by customer rating (highest first) and years of experience (ascending or descending).
- **Configurable CORS:** Accepts configurable frontend origins via `CORS_ORIGINS`. Disallows dangerous wildcard (`*`) origins when credentials are enabled.

### 5. Service Booking Lifecycle
- **Booking Submission (`POST /bookings`):** Customers book services with date validation (`YYYY-MM-DD`) and issue description (3-1,000 characters).
- **Anti-Impersonation Protection:** If an unauthenticated booking request supplies an email belonging to an existing registered user, the API returns `HTTP 401 Unauthorized`, requiring the customer to log in. Unregistered emails can book as guests.
- **Customer Cancellation:** Customers can cancel their own pending bookings directly from "My Bookings" (`status: "Rejected"`). Cross-customer cancellation is blocked (`HTTP 403 Forbidden`).
- **Single-Booking IDOR Safeguard:** Access to `GET /bookings/{id}` is strictly restricted to the booking owner, the assigned provider, or an administrator.

### 6. Provider Portal & Status Management
- **Provider View Isolation:** Providers can only view and query bookings assigned to their registered business name (`HTTP 403 Forbidden` if attempting to inspect other providers' bookings).
- **Status Progression:** Providers can transition bookings to `Accepted`, `Rejected`, or `Completed`.
- **Customer Permission Guard:** Customers cannot accept or complete bookings (`HTTP 403 Forbidden`).
- **Completed Booking Final Lock:** Once a booking status reaches `Completed`, it cannot be reverted back to `Pending`, `Accepted`, or `Rejected` through UI controls or API requests (`HTTP 400 Bad Request`).

### 7. Customer Rating & Review System
- **Completed Booking Prerequisite:** Reviews can only be submitted for bookings in `Completed` status (`HTTP 400 Bad Request` if pending or rejected).
- **Ownership Verification:** Only the customer who owns the completed booking can submit a review (`HTTP 403 Forbidden` for non-owners).
- **Rating Bounds:** Accepts 1-5 integer star ratings and optional review text (up to 1,000 characters).
- **Duplicate Prevention:** Enforces one review per completed booking (`HTTP 400 Bad Request` on repeat submissions).
- **Provider Aggregate Scores:** Dynamically calculates and displays the provider's average star rating and review count.

### 8. Responsive Navigation
- **Navigation Controls:** Displays direct "Dashboard" navigation button for authenticated users alongside service links, user display name, and Logout.
- **Homepage Return Link:** Prominent "Back to Dashboard" button in the hero section for logged-in users.
- **Provider Profile Navigation:** Direct buttons to return to Dashboard, view provider bookings, or Book Now.

---

## Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | React | `^19.2.8` | Component-based User Interface |
| **Frontend Tooling** | Vite | `^8.3.0` | High-speed frontend build tool & dev server |
| **Styling** | Vanilla CSS3 | Standard | Custom responsive mobile, tablet, and desktop styling |
| **Linting** | ESLint | `^10.10.0` | Frontend code quality and React hooks rules |
| **Backend** | Python | 3.12 | Core backend language |
| **Web Framework** | FastAPI | `0.142.2` | High-performance asynchronous REST API framework |
| **ASGI Server** | Uvicorn | `0.54.0` | Production ASGI web server |
| **Database** | MongoDB | Community Server | Document-based NoSQL database |
| **DB Driver** | PyMongo | `4.18.2` | Python driver for MongoDB |
| **Data Validation** | Pydantic | `2.13.5` | Data validation and request schemas |
| **Password Security** | Bcrypt | `5.0.0` | One-way salted password hashing |
| **Authentication** | PyJWT | `2.15.1` | Signed HS256 JSON Web Tokens with standard claims |
| **Rate Limiting** | SlowAPI | `0.1.10` | IP-based request throttling on auth endpoints |
| **Configuration** | python-dotenv | `1.2.4` | Loads environment variables from `.env` files |

---

## Project Architecture & Directory Structure

```
local-service-marketplace/
â”œâ”€â”€ .env.example                     # Example root environment configuration template
â”œâ”€â”€ .gitignore                       # Repository-wide Git exclusions
â”œâ”€â”€ README.md                        # Project documentation (this file)
â”‚
â”œâ”€â”€ backend/                         # FastAPI Application
â”‚   â”œâ”€â”€ .env.example                 # Example backend environment configuration
â”‚   â”œâ”€â”€ main.py                      # FastAPI routes, DB models, validation, auth & logic
â”‚   â”œâ”€â”€ requirements.txt             # Python package dependencies
â”‚   â”œâ”€â”€ test_phase6a_security.py     # Ownership & completed lock regression tests
â”‚   â”œâ”€â”€ test_phase6b.py              # Input validation & email normalization tests
â”‚   â”œâ”€â”€ test_phase6c_env.py          # Git hygiene & env variable fallback tests
â”‚   â”œâ”€â”€ test_phase8a_auth.py         # JWT auth, rate limiting & config validation tests
â”‚   â””â”€â”€ test_reviews.py              # Reviews & ratings aggregation test suite
â”‚
â”œâ”€â”€ docs/                            # Project Documentation
â”‚   â””â”€â”€ PROJECT_REQUIREMENTS.md      # Detailed system requirements specification
â”‚
â””â”€â”€ frontend/                        # React + Vite Application
    â”œâ”€â”€ .env.example                 # Example frontend environment configuration
    â”œâ”€â”€ .gitignore                   # Frontend Git exclusions
    â”œâ”€â”€ eslint.config.js             # ESLint configuration
    â”œâ”€â”€ index.html                   # HTML entry point with viewport meta tag
    â”œâ”€â”€ package.json                 # Frontend dependencies and npm scripts
    â”œâ”€â”€ package-lock.json            # Exact dependency lockfile
    â”œâ”€â”€ README.md                    # Frontend-specific documentation
    â”œâ”€â”€ vite.config.js               # Vite build configuration
    â”œâ”€â”€ public/                      # Static assets
    â”‚   â”œâ”€â”€ favicon.svg              # Platform favicon
    â”‚   â””â”€â”€ icons.svg                # Inline SVG symbol definitions
    â””â”€â”€ src/                         # Source code
        â”œâ”€â”€ assets/                  # Hero illustrations and static images
        â”œâ”€â”€ components/              # Modular UI components
        â”‚   â”œâ”€â”€ Booking.jsx          # Service booking form with guest / auth handling
        â”‚   â”œâ”€â”€ Dashboard.jsx        # Customer & provider dashboard hub
        â”‚   â”œâ”€â”€ FilterBar.jsx        # Search, category filter & sort bar
        â”‚   â”œâ”€â”€ Footer.jsx           # Footer component
        â”‚   â”œâ”€â”€ Login.jsx            # User login component with status alerts
        â”‚   â”œâ”€â”€ ManageBookings.jsx   # Provider portal booking status controls
        â”‚   â”œâ”€â”€ MyBookings.jsx       # Customer booking manager & review submission
        â”‚   â”œâ”€â”€ Navbar.jsx           # Top navigation bar with auth session controls
        â”‚   â”œâ”€â”€ Profile.jsx          # Profile viewing & name editing
        â”‚   â”œâ”€â”€ ProviderCard.jsx     # Provider summary card
        â”‚   â”œâ”€â”€ ProviderProfile.jsx  # Detailed provider profile & reviews
        â”‚   â”œâ”€â”€ Register.jsx         # User registration with provider code field
        â”‚   â””â”€â”€ ServiceCard.jsx      # Service category card
        â”œâ”€â”€ App.css                  # Responsive styling across all viewports
        â”œâ”€â”€ App.jsx                  # Main view router & state management
        â”œâ”€â”€ config.js                # Central API configuration (VITE_API_URL)
        â”œâ”€â”€ index.css                # Global CSS reset
        â””â”€â”€ main.jsx                 # React root mount point
```

---

## Prerequisites

Before running the application locally, ensure you have the following installed on Windows:

1. **Python 3.10+** (Python 3.12 recommended). Ensure `python` is available on your PATH.
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

# 5. (Optional) Create local .env from example template
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

# 3. (Optional) Create local .env from example template
Copy-Item .env.example .env

# 4. Start the Vite development server
npm run dev
```

The React frontend will start at: **`http://localhost:5173/`**

---

## Environment Configuration

FixNear uses environment variables with safe offline fallbacks for local development.

### Safe Configuration Templates

The repository includes `.env.example` template files (`.env.example`, `backend/.env.example`, `frontend/.env.example`) to document available configuration variables.

- **How to Use:** Copy the example file to `.env` in the root or respective subfolder (e.g., `Copy-Item .env.example .env`).
- **Security Rule:** Never commit real secrets, private keys, or actual credentials to version control. Actual `.env` files are excluded by `.gitignore`.

### Backend Configuration Variables

| Variable | Default (Development) | Purpose | Production Requirement |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `development` | Environment mode (`development` or `production`) | Set to `production` |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection URI string | Required; must point to secure DB cluster |
| `JWT_SECRET` | Development fallback secret | Secret key used to sign and verify JWT tokens | Required; must be >= 32 characters, no fallback |
| `JWT_EXPIRE_MINUTES`| `1440` (24 hours) | Access token validity duration in minutes | Configurable based on session policy |
| `PROVIDER_INVITE_SECRET`| Development fallback code | Shared authorization code for provider registration | Required; must be >= 16 characters, no fallback |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed web origins | Required; exact frontend domain (no `*`) |
| `LOGIN_RATE_LIMIT` | `60/minute` | Rate limit for `/login` endpoint per IP address | Defaults to `10/minute` in production |
| `REGISTER_RATE_LIMIT`| `60/minute` | Rate limit for `/register` endpoint per IP address | Defaults to `5/minute` in production |
| `RATELIMIT_STORAGE_URI`| `memory://` | Storage backend for rate limiting | Configure `redis://...` for multi-worker setups |

> **Production Fail-Safe:** When `APP_ENV=production`, `backend/main.py` validates `JWT_SECRET`, `PROVIDER_INVITE_SECRET`, `CORS_ORIGINS`, and `MONGO_URI` on startup. If any required variable is missing, empty, shorter than required bounds, or uses a development fallback, the server immediately aborts startup with a `RuntimeError`.

### Frontend Configuration Variables

| Variable | Default (Development) | Purpose |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend API base URL consumed by `frontend/src/config.js` |

---

## API Endpoints & Local URLs

### Local Access URLs

- **Frontend Application:** `http://localhost:5173/`
- **Backend API Base:** `http://127.0.0.1:8000/`
- **Swagger Interactive API Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc API Documentation:** `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`

### REST API Endpoints

| Method | Endpoint | Description | Authentication & Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API status and welcome message | **Public** |
| `GET` | `/db-test` | MongoDB connection ping verification | **Public** |
| `GET` | `/services` | List service categories with optional search | **Public** |
| `GET` | `/providers` | List providers with category/location/sort filters | **Public** |
| `POST` | `/register` | Register new account (rate-limited, password hashed) | **Public** (provider role requires valid invite code) |
| `POST` | `/login` | Authenticate credentials and issue signed JWT (rate-limited) | **Public** (returns 401 on bad credentials) |
| `GET` | `/profile` | Retrieve authenticated user profile | **Authenticated** (`Bearer <token>`; cross-user blocked) |
| `PUT` | `/profile` | Update user display name (email is immutable) | **Authenticated** (`Bearer <token>`; cross-user blocked) |
| `PATCH`| `/profile` | Update user display name | **Authenticated** (`Bearer <token>`; cross-user blocked) |
| `POST` | `/bookings` | Create new service booking | **Optional Auth** (derives user identity if token present; allows guest booking for unregistered emails; blocks anonymous spoofing of registered accounts) |
| `GET` | `/bookings` | List bookings (customer: own bookings; provider: assigned bookings) | **Authenticated** (`Bearer <token>`; role-scoped view) |
| `GET` | `/bookings/{id}` | Retrieve individual booking details | **Authenticated** (`Bearer <token>`; restricted to owner, assigned provider, or admin) |
| `PATCH`| `/bookings/{id}/status` | Update booking status (`Accepted`, `Rejected`, `Completed`) | **Authenticated** (`Bearer <token>`; customer can only cancel; provider can only update assigned bookings; completed lock enforced) |
| `PUT` | `/bookings/{id}/status` | Update booking status | **Authenticated** (`Bearer <token>`; same rules as PATCH) |
| `POST` | `/reviews` | Submit star rating (1-5) and review for completed booking | **Customer Authenticated** (`Bearer <token>`; restricted to completed booking owner; duplicates blocked) |
| `GET` | `/reviews` | Retrieve reviews filtered by provider, email, or booking | **Public** |
| `GET` | `/reviews/summary` | Aggregate provider star score and review count | **Public** |

---

## Automated Testing & Verification

FixNear includes automated test suites covering authentication, authorization, data validation, rate limiting, and environment configuration.

### Running Backend Test Suites

Run the test suites from the project root using the virtual environment Python executable:

```powershell
# 1. Phase 8A: Secure JWT Auth, IDOR Boundaries, Rate Limiting & Config Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase8a_auth.py

# 2. Phase 6A: Critical Authorization & Ownership Security Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase6a_security.py

# 3. Phase 6B: Data Validation, Email Normalization & HTTP Codes Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase6b.py

# 4. Phase 6C: Git Hygiene, Environment Variables & Config Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_phase6c_env.py

# 5. Phase 4: Customer Rating & Review System Tests
& ".\backend\venv\Scripts\python.exe" .\backend\test_reviews.py
```

*All backend test suites start their own controlled test processes, execute isolated test scenarios, clean up all created test documents, and verify database integrity upon completion.*

### Running Frontend Checks

From the `frontend/` directory:

```powershell
cd frontend

# Run ESLint check
npm run lint

# Run Vite production build check
npm run build
```

---

## Security Architecture & Current Limitations

### Implemented Security Controls

1. **Signed JWT Bearer Authentication:** Signed with `HS256`, explicit algorithm whitelisting, standard `iat` and `exp` claims, and automatic token expiry handling.
2. **Server-Derived Identity & Authorization:** All roles (`customer`, `provider`, `admin`) and identities are resolved on the server from the verified token and database records. Client-declared identity headers are not used or trusted.
3. **Password Security:** Salted one-way hashing using `bcrypt` (length bounds: 6-72 characters). Graceful handling of legacy or corrupted hashes.
4. **Input Boundaries & Email Normalization:** Validated field lengths and formats across all models; whitespace stripping and lowercase normalization on all email inputs.
5. **IDOR & Ownership Controls:** Single-booking detail lookups (`GET /bookings/{id}`), profile lookups, and booking lists enforce strict ownership boundaries.
6. **Completed Booking Final Lock:** Bookings marked `Completed` cannot be reverted back to `Pending`, `Accepted`, or `Rejected`.
7. **Rate Limiting:** IP-based request throttling on `/login` and `/register` returning `HTTP 429 Too Many Requests`.
8. **Production Fail-Safe:** Automated configuration check on server startup aborting when critical production secrets or database configurations are missing.

### Current Security Limitations

1. **Browser `localStorage` Token Storage:** Access tokens are stored in browser `localStorage`. If an application-level Cross-Site Scripting (XSS) vulnerability were present, scripts could potentially read the stored token. Future enhancements should consider storing session tokens in `HttpOnly`, `Secure`, `SameSite` cookies.
2. **Provider Registration Mechanism:** Provider account creation is guarded by a shared secret authorization code (`PROVIDER_INVITE_SECRET`). This functions as an administrative gatekeeper to prevent public self-registration, but does **not** constitute an identity verification, background check, or licensing validation process. Anyone with the code can register as a provider.
3. **Single-Worker Rate Limiting:** The default rate limiter uses in-memory storage (`memory://`). In multi-worker production environments (e.g., Gunicorn with multiple Uvicorn workers or multi-container clusters), rate limits are tracked per process. Deploying with multiple workers requires configuring `RATELIMIT_STORAGE_URI` with a shared storage backend such as Redis (`redis://...`).
4. **Transport Layer Security (HTTPS):** Local development uses unencrypted HTTP. Production deployment requires HTTPS / TLS termination to protect authentication tokens in transit.
5. **Production Readiness:** The application is configured for local development by default. Deploying to production requires setting `APP_ENV=production`, generating high-entropy cryptographic keys for `JWT_SECRET` and `PROVIDER_INVITE_SECRET`, specifying exact production `CORS_ORIGINS`, and provisioning a managed MongoDB database.

### Planned Future Improvements

- **Dedicated Admin Portal & Provider Onboarding:** Implement an administrative dashboard with individual, single-use invite codes or a provider application and document approval workflow.
- **HttpOnly Cookie Authentication:** Transition from `localStorage` bearer token storage to `HttpOnly`, `SameSite=Lax` cookies for enhanced XSS resilience.
- **Distributed Rate Limiting:** Integrate Redis for cluster-wide rate limiting and IP reputation tracking.
- **AI/ML Service Classification:** Automatically analyze customer problem descriptions (e.g., *"Water dripping under kitchen sink"*) and classify them into the appropriate service category (*Plumbing*).
- **Payment Gateway Integration:** Escrow and online payment processing (e.g., Stripe, Razorpay).
- **Real-Time Communication:** WebSockets for live chat between customers and providers.
- **Real-Time Notifications:** Email / SMS notifications for booking updates.

---

## Author

**Rahul Chatterjee**
- GitHub: [@rahul5Q](https://github.com/rahul5Q)
- Project: FixNear Local Service Marketplace
