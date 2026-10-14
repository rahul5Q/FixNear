import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment configuration (.env in backend or root if present)
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")
load_dotenv()

# Application Environment & Security Configuration
APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
IS_PRODUCTION = APP_ENV in ["production", "prod"]

DEV_JWT_SECRET_FALLBACK = "fixnear-local-dev-jwt-secret-do-not-use-in-production-2026"
DEV_PROVIDER_INVITE_SECRET_FALLBACK = "fixnear-provider-invite-2026"

def get_validated_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if IS_PRODUCTION:
        if not secret or not secret.strip():
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode (APP_ENV=production), "
                "JWT_SECRET must be set via environment variable. Server startup aborted."
            )
        clean_secret = secret.strip()
        if clean_secret == DEV_JWT_SECRET_FALLBACK:
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode, the insecure development "
                "JWT_SECRET fallback cannot be used. Server startup aborted."
            )
        if len(clean_secret) < 32:
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode, JWT_SECRET must be at least "
                "32 characters long to ensure cryptographic strength. Server startup aborted."
            )
        return clean_secret
    else:
        return secret.strip() if (secret and secret.strip()) else DEV_JWT_SECRET_FALLBACK

def get_validated_provider_invite_secret() -> str:
    secret = os.getenv("PROVIDER_INVITE_SECRET")
    if IS_PRODUCTION:
        if not secret or not secret.strip():
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode (APP_ENV=production), "
                "PROVIDER_INVITE_SECRET must be set via environment variable. Server startup aborted."
            )
        clean_secret = secret.strip()
        if clean_secret == DEV_PROVIDER_INVITE_SECRET_FALLBACK:
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode, the insecure development "
                "PROVIDER_INVITE_SECRET fallback cannot be used. Server startup aborted."
            )
        if len(clean_secret) < 16:
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode, PROVIDER_INVITE_SECRET must be at least "
                "16 characters long. Server startup aborted."
            )
        return clean_secret
    else:
        return secret.strip() if (secret and secret.strip()) else DEV_PROVIDER_INVITE_SECRET_FALLBACK

def get_cors_origins() -> list[str]:
    raw_cors = os.getenv("CORS_ORIGINS")
    if raw_cors and raw_cors.strip():
        origins = [orig.strip() for orig in raw_cors.split(",") if orig.strip()]
        if any(orig == "*" for orig in origins):
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: Wildcard origin '*' is not allowed in CORS_ORIGINS "
                "when allow_credentials=True. Specify explicit frontend origins (e.g., https://fixnear.example.com)."
            )
        return origins

    if IS_PRODUCTION:
        raise RuntimeError(
            "FATAL CONFIGURATION ERROR: In production mode (APP_ENV=production), "
            "CORS_ORIGINS must be set via environment variable with exact frontend origins. "
            "Server startup aborted."
        )

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

def get_validated_mongo_uri() -> str:
    uri = os.getenv("MONGO_URI")
    if IS_PRODUCTION:
        if not uri or not uri.strip():
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: In production mode (APP_ENV=production), "
                "MONGO_URI must be set via environment variable. Server startup aborted."
            )
        return uri.strip()
    else:
        return uri.strip() if (uri and uri.strip()) else "mongodb://localhost:27017/"

def validate_production_configuration() -> dict:
    return {
        "jwt_secret": get_validated_jwt_secret(),
        "provider_invite_secret": get_validated_provider_invite_secret(),
        "cors_origins": get_cors_origins(),
        "mongo_uri": get_validated_mongo_uri(),
    }

# Fail fast on startup if production configuration is invalid
if IS_PRODUCTION:
    validate_production_configuration()

JWT_SECRET = get_validated_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
PROVIDER_INVITE_SECRET = get_validated_provider_invite_secret()
CORS_ORIGINS = get_cors_origins()
MONGO_URI = get_validated_mongo_uri()

# Rate Limiting Configuration
RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in ["false", "0", "no"]

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=RATELIMIT_STORAGE_URI,
    headers_enabled=False,
    enabled=RATE_LIMIT_ENABLED,
)

def get_login_rate_limit() -> str:
    return os.getenv("LOGIN_RATE_LIMIT", "10/minute" if IS_PRODUCTION else "60/minute")

def get_register_rate_limit() -> str:
    return os.getenv("REGISTER_RATE_LIMIT", "5/minute" if IS_PRODUCTION else "60/minute")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient(MONGO_URI)
db = client["local_service_marketplace"]

services_collection = db["services"]
providers_collection = db["providers"]
users_collection = db["users"]
bookings_collection = db["bookings"]
reviews_collection = db["reviews"]

def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> dict:
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Authorization header is missing."
        )
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Expected 'Bearer <token>'."
        )
    token = parts[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Authentication failed.")

    email_clean = email.strip().lower()
    user = users_collection.find_one({"email": email_clean})
    if not user:
        if not IS_PRODUCTION and email_clean in DEFAULT_PROVIDERS:
            p_acc = DEFAULT_PROVIDERS[email_clean]
            return {
                "id": f"provider_{p_acc['email']}",
                "email": p_acc["email"],
                "name": p_acc["name"],
                "role": p_acc["role"],
                "provider_name": p_acc["provider_name"]
            }
        raise HTTPException(status_code=401, detail="User account no longer exists.")

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role") or "customer",
        "provider_name": user.get("provider_name")
    }

def get_optional_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[dict]:
    if not authorization or not authorization.strip():
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None

# Development provider credentials configuration
DEV_PROVIDER_PASSWORD = os.getenv("DEV_PROVIDER_PASSWORD", "ProviderPass123!" if not IS_PRODUCTION else "")

# Default provider identities (used in development/test to link with existing demo provider profiles)
DEFAULT_PROVIDERS = {
    "amit@provider.fixnear.com": {
        "name": "Amit Sharma",
        "email": "amit@provider.fixnear.com",
        "role": "provider",
        "provider_name": "Amit Electrical Services"
    },
    "saha@provider.fixnear.com": {
        "name": "Subhash Saha",
        "email": "saha@provider.fixnear.com",
        "role": "provider",
        "provider_name": "Saha Plumbing Services"
    },
    "roy@provider.fixnear.com": {
        "name": "Pritam Roy",
        "email": "roy@provider.fixnear.com",
        "role": "provider",
        "provider_name": "Roy Home Solutions"
    }
}

if providers_collection.count_documents({}) == 0:
    providers_collection.insert_many([
        {
            "id": 1,
            "name": "Amit Electrical Services",
            "service": "Electrician",
            "rating": 4.8,
            "experience": "8 years",
            "location": "Kolkata"
        },
        {
            "id": 2,
            "name": "Saha Plumbing Services",
            "service": "Plumber",
            "rating": 4.7,
            "experience": "6 years",
            "location": "New Town"
        },
        {
            "id": 3,
            "name": "Roy Home Solutions",
            "service": "AC Repair",
            "rating": 4.9,
            "experience": "10 years",
            "location": "Salt Lake"
        }
    ])
if services_collection.count_documents({}) == 0:
    services_collection.insert_many([
        {
            "id": 1,
            "name": "Plumber",
            "description": "Pipe, tap and water-related repairs"
        },
        {
            "id": 2,
            "name": "Electrician",
            "description": "Electrical installation and repairs"
        },
        {
            "id": 3,
            "name": "Carpenter",
            "description": "Furniture and woodwork services"
        },
        {
            "id": 4,
            "name": "AC Repair",
            "description": "AC servicing and maintenance"
        },
        {
            "id": 5,
            "name": "Cleaning",
            "description": "Home and office cleaning services"
        },
        {
            "id": 6,
            "name": "Appliance Repair",
            "description": "Repair for common home appliances"
        }
    ])


@app.get("/")
def home():
    return {
        "message": "Local Service Marketplace API is running"
    }


@app.get("/services")
def get_services(
    search: Optional[str] = None,
    category: Optional[str] = None
):
    query = {}
    if category and category.strip() and category.strip().lower() != "all":
        query["name"] = {"$regex": f"^{re.escape(category.strip())}$", "$options": "i"}

    if search and search.strip():
        search_regex = {"$regex": re.escape(search.strip()), "$options": "i"}
        search_filter = {
            "$or": [
                {"name": search_regex},
                {"description": search_regex}
            ]
        }
        if query:
            query = {"$and": [query, search_filter]}
        else:
            query = search_filter

    services = list(services_collection.find(query, {"_id": 0}))
    return services


@app.get("/providers")
def get_providers(
    search: Optional[str] = None,
    service: Optional[str] = None,
    location: Optional[str] = None,
    sort_by: Optional[str] = None
):
    filters = []

    if service and service.strip() and service.strip().lower() != "all":
        filters.append({"service": {"$regex": f"^{re.escape(service.strip())}$", "$options": "i"}})

    if location and location.strip() and location.strip().lower() != "all":
        filters.append({"location": {"$regex": f"^{re.escape(location.strip())}$", "$options": "i"}})

    if search and search.strip():
        search_regex = {"$regex": re.escape(search.strip()), "$options": "i"}
        filters.append({
            "$or": [
                {"name": search_regex},
                {"service": search_regex},
                {"location": search_regex}
            ]
        })

    mongo_query = {}
    if len(filters) == 1:
        mongo_query = filters[0]
    elif len(filters) > 1:
        mongo_query = {"$and": filters}

    providers = list(providers_collection.find(mongo_query, {"_id": 0}))

    def parse_exp(exp_val):
        if isinstance(exp_val, (int, float)):
            return float(exp_val)
        if not exp_val:
            return 0.0
        m = re.search(r"(\d+(\.\d+)?)", str(exp_val))
        return float(m.group(1)) if m else 0.0

    if sort_by == "rating_desc":
        providers.sort(key=lambda p: float(p.get("rating", 0)), reverse=True)
    elif sort_by == "rating_asc":
        providers.sort(key=lambda p: float(p.get("rating", 0)))
    elif sort_by == "experience_desc":
        providers.sort(key=lambda p: parse_exp(p.get("experience")), reverse=True)
    elif sort_by == "experience_asc":
        providers.sort(key=lambda p: parse_exp(p.get("experience")))

    return providers

@app.get("/db-test")
def db_test():
    client.admin.command("ping")
    return {
        "message": "MongoDB connected successfully"
    }
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_and_normalize_email(email_str: Optional[str]) -> str:
    if not email_str or not email_str.strip():
        raise HTTPException(status_code=400, detail="Email is required.")
    cleaned = email_str.strip().lower()
    if len(cleaned) < 5 or len(cleaned) > 255 or not EMAIL_REGEX.match(cleaned):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    return cleaned


def validate_password(password: Optional[str]) -> str:
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    if len(password) > 72:
        raise HTTPException(status_code=400, detail="Password cannot exceed 72 characters.")
    return password


def validate_name(name: Optional[str]) -> str:
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    cleaned = name.strip()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters long.")
    if len(cleaned) > 100:
        raise HTTPException(status_code=400, detail="Name cannot exceed 100 characters.")
    return cleaned


class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "customer"
    provider_name: Optional[str] = None
    provider_invite_code: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class BookingCreate(BaseModel):
    user_email: Optional[str] = None
    service: str
    provider: str
    date: str
    description: str


class BookingStatusUpdate(BaseModel):
    status: str
    updater_email: Optional[str] = None
    role: Optional[str] = None
    provider_name: Optional[str] = None


class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    name: str


class ReviewCreate(BaseModel):
    booking_id: str
    customer_email: Optional[str] = None
    rating: int
    comment: Optional[str] = ""


@app.post("/register")
@limiter.limit(get_register_rate_limit)
def register_user(request: Request, user: UserRegister):
    clean_name = validate_name(user.name)
    clean_email = validate_and_normalize_email(user.email)
    valid_password = validate_password(user.password)

    role = (user.role or "customer").strip().lower()
    if role not in ["customer", "provider"]:
        raise HTTPException(status_code=400, detail="Role must be either 'customer' or 'provider'.")

    provider_name = None
    if role == "provider":
        expected_invite_code = PROVIDER_INVITE_SECRET
        supplied_code = (user.provider_invite_code or "").strip()
        if not expected_invite_code or supplied_code != expected_invite_code:
            raise HTTPException(
                status_code=403,
                detail="Provider self-registration is restricted. A valid provider authorization invite code is required to register as a service provider."
            )
        if not user.provider_name or not user.provider_name.strip():
            raise HTTPException(status_code=400, detail="Provider name is required for provider registration.")
        provider_name = user.provider_name.strip()
        if len(provider_name) < 2 or len(provider_name) > 100:
            raise HTTPException(status_code=400, detail="Provider name must be between 2 and 100 characters.")

    if clean_email in DEFAULT_PROVIDERS or users_collection.find_one({"email": clean_email}):
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    hashed_password = bcrypt.hashpw(
        valid_password.encode("utf-8"),
        bcrypt.gensalt()
    )

    doc = {
        "name": clean_name,
        "email": clean_email,
        "password": hashed_password.decode("utf-8"),
        "role": role,
        "provider_name": provider_name
    }
    users_collection.insert_one(doc)

    return {
        "message": "Registration successful",
        "role": role
    }


@app.post("/login")
@limiter.limit(get_login_rate_limit)
def login_user(request: Request, user: UserLogin):
    clean_email = validate_and_normalize_email(user.email)
    if not user.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    existing_user = users_collection.find_one({
        "email": clean_email
    })

    if not existing_user:
        if not IS_PRODUCTION and clean_email in DEFAULT_PROVIDERS:
            p_acc = DEFAULT_PROVIDERS[clean_email]
            if DEV_PROVIDER_PASSWORD and user.password == DEV_PROVIDER_PASSWORD:
                role = p_acc["role"]
                provider_name = p_acc["provider_name"]
                access_token = create_access_token({
                    "sub": p_acc["email"],
                    "name": p_acc["name"],
                    "role": role,
                    "provider_name": provider_name
                })
                return {
                    "message": "Login successful",
                    "access_token": access_token,
                    "token_type": "bearer",
                    "name": p_acc["name"],
                    "email": p_acc["email"],
                    "role": role,
                    "provider_name": provider_name
                }
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    try:
        password_match = bcrypt.checkpw(
            user.password.encode("utf-8"),
            existing_user["password"].encode("utf-8")
        )
    except (ValueError, TypeError):
        password_match = False

    if not password_match:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    role = existing_user.get("role") or "customer"
    provider_name = existing_user.get("provider_name")

    access_token = create_access_token({
        "sub": existing_user["email"],
        "name": existing_user["name"],
        "role": role,
        "provider_name": provider_name
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "name": existing_user["name"],
        "email": existing_user["email"],
        "role": role,
        "provider_name": provider_name
    }


@app.get("/profile")
def get_profile(
    email: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if email and email.strip():
        email_clean = validate_and_normalize_email(email)
        if current_user["email"] != email_clean:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot access another user's profile."
            )

    return {
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user["role"],
        "provider_name": current_user.get("provider_name")
    }


@app.put("/profile")
@app.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    if payload.email and payload.email.strip():
        email_clean = validate_and_normalize_email(payload.email)
        if current_user["email"] != email_clean:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot update another user's profile."
            )

    name_clean = validate_name(payload.name)

    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"name": name_clean}}
    )

    return {
        "message": "Profile updated successfully",
        "name": name_clean,
        "email": current_user["email"],
        "role": current_user["role"]
    }


@app.post("/bookings")
def create_booking(
    booking: BookingCreate,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    if current_user:
        clean_email = current_user["email"]
    elif booking.user_email and booking.user_email.strip():
        clean_email = validate_and_normalize_email(booking.user_email)
        # Prevent unauthenticated users from creating bookings under registered accounts
        if users_collection.find_one({"email": clean_email}):
            raise HTTPException(
                status_code=401,
                detail="This email belongs to a registered FixNear account. Please log in to complete your booking."
            )
    else:
        raise HTTPException(status_code=400, detail="User email is required.")

    clean_service = (booking.service or "").strip()
    if len(clean_service) < 2 or len(clean_service) > 100:
        raise HTTPException(status_code=400, detail="Service name must be between 2 and 100 characters.")

    clean_provider = (booking.provider or "").strip()
    if len(clean_provider) < 2 or len(clean_provider) > 100:
        raise HTTPException(status_code=400, detail="Provider name must be between 2 and 100 characters.")

    clean_date = (booking.date or "").strip()
    if not clean_date:
        raise HTTPException(status_code=400, detail="Booking date is required.")
    try:
        datetime.strptime(clean_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Booking date must be in YYYY-MM-DD format.")

    clean_desc = (booking.description or "").strip()
    if len(clean_desc) < 3:
        raise HTTPException(status_code=400, detail="Problem description must be at least 3 characters long.")
    if len(clean_desc) > 1000:
        raise HTTPException(status_code=400, detail="Problem description cannot exceed 1000 characters.")

    new_booking = {
        "user_email": clean_email,
        "service": clean_service,
        "provider": clean_provider,
        "date": clean_date,
        "description": clean_desc,
        "status": "Pending"
    }

    result = bookings_collection.insert_one(new_booking)

    return {
        "message": "Booking created successfully",
        "booking_id": str(result.inserted_id)
    }


@app.get("/bookings")
def get_bookings(
    user_email: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get("role", "customer")

    if role == "customer":
        if user_email and user_email.strip():
            req_email = validate_and_normalize_email(user_email)
            if req_email != current_user["email"]:
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: You cannot access another customer's bookings."
                )
        query = {"user_email": {"$regex": f"^{re.escape(current_user['email'])}$", "$options": "i"}}
        bookings = list(bookings_collection.find(query))
        for b in bookings:
            b["id"] = str(b["_id"])
            del b["_id"]
        return bookings

    elif role == "provider":
        assigned_provider = current_user.get("provider_name")
        if not assigned_provider:
            raise HTTPException(status_code=403, detail="Provider account is not linked to a provider business.")
        if provider and provider.strip() and provider.strip().lower() != "all":
            if provider.strip().lower() != assigned_provider.lower():
                raise HTTPException(
                    status_code=403,
                    detail=f"Forbidden: You can only view bookings assigned to '{assigned_provider}'."
                )
        query = {"provider": {"$regex": f"^{re.escape(assigned_provider)}$", "$options": "i"}}
        bookings = list(bookings_collection.find(query))
        for b in bookings:
            b["id"] = str(b["_id"])
            del b["_id"]
        return bookings

    elif role == "admin":
        query = {}
        if user_email and user_email.strip():
            query["user_email"] = {"$regex": f"^{re.escape(user_email.strip().lower())}$", "$options": "i"}
        elif provider and provider.strip() and provider.strip().lower() != "all":
            query["provider"] = {"$regex": f"^{re.escape(provider.strip())}$", "$options": "i"}
        bookings = list(bookings_collection.find(query))
        for b in bookings:
            b["id"] = str(b["_id"])
            del b["_id"]
        return bookings

    else:
        raise HTTPException(status_code=403, detail="Unauthorized role.")


@app.get("/bookings/{booking_id}")
def get_booking_by_id(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        obj_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")

    booking = bookings_collection.find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking_email = booking.get("user_email", "").strip().lower()
    booking_provider = booking.get("provider", "").strip().lower()

    role = current_user.get("role", "customer")
    is_owner = (current_user["email"] == booking_email)
    is_assigned_provider = (role == "provider" and (current_user.get("provider_name") or "").strip().lower() == booking_provider)
    is_admin = (role == "admin")

    if not (is_owner or is_assigned_provider or is_admin):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot access another customer's booking."
        )

    booking["id"] = str(booking["_id"])
    del booking["_id"]
    return booking


@app.patch("/bookings/{booking_id}/status")
@app.put("/bookings/{booking_id}/status")
def update_booking_status(
    booking_id: str,
    payload: BookingStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    try:
        obj_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")

    booking = bookings_collection.find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    allowed_statuses = ["Pending", "Accepted", "Rejected", "Completed"]
    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed statuses: {', '.join(allowed_statuses)}"
        )

    # Completed booking lock rule
    if booking.get("status") == "Completed" and payload.status in ["Pending", "Accepted", "Rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot change the status of a completed booking. Completed bookings are finalized and cannot be set back to Pending, Accepted, or Rejected."
        )

    booking_customer_email = booking.get("user_email", "").strip().lower()
    booking_provider_name = (booking.get("provider") or "").strip()

    role = current_user.get("role", "customer")

    if role == "customer":
        if current_user["email"] != booking_customer_email:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot modify another customer's booking."
            )
        if payload.status in ["Accepted", "Completed"]:
            raise HTTPException(
                status_code=403,
                detail="Customers are not authorized to accept or complete bookings. Only service providers or administrators can perform this action."
            )
        if payload.status != "Rejected":
            raise HTTPException(
                status_code=403,
                detail="Customers can only cancel (Reject) their bookings."
            )

    elif role == "provider":
        assigned_provider = (current_user.get("provider_name") or "").strip()
        if not assigned_provider or assigned_provider.lower() != booking_provider_name.lower():
            raise HTTPException(
                status_code=403,
                detail=f"Provider authorization failed: You can only update bookings assigned to '{booking_provider_name}'."
            )

    elif role == "admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role.")

    bookings_collection.update_one(
        {"_id": obj_id},
        {"$set": {"status": payload.status}}
    )

    return {
        "message": f"Booking status updated to {payload.status}",
        "id": booking_id,
        "status": payload.status
    }


@app.post("/reviews")
def create_review(
    payload: ReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    if not isinstance(payload.rating, int) or payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be an integer between 1 and 5."
        )

    comment_clean = (payload.comment or "").strip()
    if len(comment_clean) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Review comment cannot exceed 1000 characters."
        )

    booking_id_str = payload.booking_id.strip()
    try:
        obj_id = ObjectId(booking_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format.")

    booking = bookings_collection.find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.get("status") != "Completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed bookings can be rated and reviewed."
        )

    booking_user_email = booking.get("user_email", "").strip().lower()
    if current_user["email"] != booking_user_email:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot review another customer's booking."
        )

    existing_review = reviews_collection.find_one({"booking_id": booking_id_str})
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="A review has already been submitted for this booking."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    review_doc = {
        "booking_id": booking_id_str,
        "customer_email": current_user["email"],
        "provider": booking.get("provider", ""),
        "service": booking.get("service", ""),
        "rating": payload.rating,
        "comment": comment_clean,
        "created_at": now_iso
    }

    result = reviews_collection.insert_one(review_doc)

    return {
        "message": "Review submitted successfully",
        "id": str(result.inserted_id),
        "booking_id": booking_id_str,
        "customer_email": current_user["email"],
        "provider": booking.get("provider", ""),
        "rating": payload.rating,
        "comment": comment_clean,
        "created_at": now_iso
    }



@app.get("/reviews")
def get_reviews(
    provider: Optional[str] = None,
    customer_email: Optional[str] = None,
    booking_id: Optional[str] = None
):
    query = {}
    if provider and provider.strip():
        query["provider"] = provider.strip()
    if customer_email and customer_email.strip():
        query["customer_email"] = customer_email.strip().lower()
    if booking_id and booking_id.strip():
        query["booking_id"] = booking_id.strip()

    reviews = list(reviews_collection.find(query).sort("_id", -1))
    for r in reviews:
        r["id"] = str(r["_id"])
        del r["_id"]

    return reviews


@app.get("/reviews/summary")
def get_reviews_summary(provider: str):
    provider_clean = provider.strip()
    reviews = list(reviews_collection.find({"provider": provider_clean}).sort("_id", -1))
    total_reviews = len(reviews)
    avg_rating = round(sum(r["rating"] for r in reviews) / total_reviews, 1) if total_reviews > 0 else None

    for r in reviews:
        r["id"] = str(r["_id"])
        del r["_id"]

    return {
        "provider": provider_clean,
        "total_reviews": total_reviews,
        "average_rating": avg_rating,
        "reviews": reviews
    }

    



