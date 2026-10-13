import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# Load environment configuration (.env in backend or root if present)
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class UserRegister(BaseModel):
    name: str
    email: str
    password: str

MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["local_service_marketplace"]
services_collection = db["services"]
providers_collection = db["providers"]
users_collection = db["users"]
bookings_collection = db["bookings"]
reviews_collection = db["reviews"]

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


@app.post("/register")
def register_user(user: UserRegister):
    clean_name = validate_name(user.name)
    clean_email = validate_and_normalize_email(user.email)
    valid_password = validate_password(user.password)

    existing_user = users_collection.find_one({
        "email": clean_email
    })

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    hashed_password = bcrypt.hashpw(
        valid_password.encode("utf-8"),
        bcrypt.gensalt()
    )

    users_collection.insert_one({
        "name": clean_name,
        "email": clean_email,
        "password": hashed_password.decode("utf-8")
    })

    return {
        "message": "Registration successful"
    }
class UserLogin(BaseModel):
    email: str
    password: str


class BookingCreate(BaseModel):
    user_email: str
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
    email: str
    name: str


class ReviewCreate(BaseModel):
    booking_id: str
    customer_email: str
    rating: int
    comment: Optional[str] = ""


@app.post("/login")
def login_user(user: UserLogin):
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
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_match = bcrypt.checkpw(
        user.password.encode("utf-8"),
        existing_user["password"].encode("utf-8")
    )

    if not password_match:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "message": "Login successful",
        "name": existing_user["name"],
        "email": existing_user["email"]
    }


@app.get("/profile")
def get_profile(
    email: str,
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    email_clean = validate_and_normalize_email(email)

    # Security Validation: Require X-User-Email header and reject missing or mismatched identity
    if not x_user_email or not x_user_email.strip():
        raise HTTPException(
            status_code=401,
            detail="Authentication required: X-User-Email header is missing"
        )

    if x_user_email.strip().lower() != email_clean:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot access another user's profile."
        )

    user = users_collection.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "name": user["name"],
        "email": user["email"]
    }


@app.put("/profile")
@app.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    email_clean = validate_and_normalize_email(payload.email)
    name_clean = validate_name(payload.name)

    # Security Validation: Require X-User-Email header and reject missing or mismatched identity
    if not x_user_email or not x_user_email.strip():
        raise HTTPException(
            status_code=401,
            detail="Authentication required: X-User-Email header is missing"
        )

    if x_user_email.strip().lower() != email_clean:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot update another user's profile."
        )

    user = users_collection.find_one({"email": email_clean})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only the name; email is strictly immutable
    users_collection.update_one(
        {"email": email_clean},
        {"$set": {"name": name_clean}}
    )

    return {
        "message": "Profile updated successfully",
        "name": name_clean,
        "email": email_clean
    }


@app.post("/bookings")
def create_booking(booking: BookingCreate):
    clean_email = validate_and_normalize_email(booking.user_email)

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
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_role: Optional[str] = Header(None, alias="X-Role")
):
    # Customer view: Filter by user_email
    if user_email and user_email.strip():
        req_email = user_email.strip().lower()
        if not x_user_email or not x_user_email.strip():
            raise HTTPException(
                status_code=401,
                detail="Authentication required: X-User-Email header is missing"
            )
        if x_user_email.strip().lower() != req_email:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot access another customer's bookings."
            )
        query = {"user_email": {"$regex": f"^{re.escape(req_email)}$", "$options": "i"}}
        bookings = list(bookings_collection.find(query))
        for b in bookings:
            b["id"] = str(b["_id"])
            del b["_id"]
        return bookings

    # Provider view: Filter by provider name
    if provider and provider.strip() and provider.strip().lower() != "all":
        provider_clean = provider.strip()
        query = {"provider": {"$regex": f"^{re.escape(provider_clean)}$", "$options": "i"}}
        bookings = list(bookings_collection.find(query))
        for b in bookings:
            b["id"] = str(b["_id"])
            del b["_id"]
        return bookings

    # Global / All view: Neither customer nor specific provider specified
    # Prevent unauthenticated callers from dumping all bookings
    effective_role = (x_role or "").strip().lower()
    if not x_user_email and effective_role not in ["provider", "admin"]:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: Specify user_email or provider, or authenticate as provider/admin."
        )

    bookings = list(bookings_collection.find({}))
    for b in bookings:
        b["id"] = str(b["_id"])
        del b["_id"]

    return bookings


@app.get("/bookings/{booking_id}")
def get_booking_by_id(
    booking_id: str,
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_role: Optional[str] = Header(None, alias="X-Role")
):
    try:
        obj_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")

    booking = bookings_collection.find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # If identity header is present, check customer ownership or provider authorization
    if x_user_email:
        email_clean = x_user_email.strip().lower()
        booking_email = booking.get("user_email", "").strip().lower()
        if (x_role or "").strip().lower() not in ["provider", "admin"] and email_clean != booking_email:
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
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_role: Optional[str] = Header(None, alias="X-Role")
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

    # Completed booking protection rule:
    # A completed booking must not be changed back to Pending, Accepted, or Rejected through an API request.
    if booking.get("status") == "Completed" and payload.status in ["Pending", "Accepted", "Rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot change the status of a completed booking. Completed bookings are finalized and cannot be set back to Pending, Accepted, or Rejected."
        )

    effective_updater = (x_user_email or payload.updater_email or "").strip().lower()
    booking_customer_email = booking.get("user_email", "").strip().lower()
    booking_provider_name = booking.get("provider", "").strip()
    effective_role = (x_role or payload.role or "").strip().lower()

    # Rule 1: Customer authorization
    # Ordinary customers cannot accept or complete their own bookings
    is_customer = False
    if effective_role == "customer":
        is_customer = True
    elif effective_updater and effective_updater == booking_customer_email and effective_role not in ["provider", "admin"]:
        is_customer = True

    if is_customer:
        if payload.status in ["Accepted", "Completed"]:
            raise HTTPException(
                status_code=403,
                detail="Customers are not authorized to accept or complete bookings. Only service providers or administrators can perform this action."
            )
        # If customer is updating/cancelling, verify they own the booking
        if effective_updater and effective_updater != booking_customer_email:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot modify another customer's booking."
            )

    # Rule 2: Accepting or completing bookings requires provider or admin role
    if payload.status in ["Accepted", "Completed"]:
        if effective_role not in ["provider", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: Accepting or completing bookings requires provider or admin authorization."
            )
        if effective_role != "admin":
            if not payload.provider_name or payload.provider_name.strip() != booking_provider_name:
                raise HTTPException(
                    status_code=403,
                    detail=f"Provider authorization failed: You can only update bookings assigned to '{booking_provider_name}'."
                )

    # Rule 3: Provider status updates (even to Rejected or Pending) must match assigned provider
    if effective_role == "provider":
        if not payload.provider_name or payload.provider_name.strip() != booking_provider_name:
            raise HTTPException(
                status_code=403,
                detail=f"Provider authorization failed: You can only update bookings assigned to '{booking_provider_name}'."
            )

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
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    # 1. Validate rating (Requirement 2)
    if not isinstance(payload.rating, int) or payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be an integer between 1 and 5."
        )

    # 1b. Validate review comment length (max 1000 characters)
    comment_clean = (payload.comment or "").strip()
    if len(comment_clean) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Review comment cannot exceed 1000 characters."
        )

    # 2. Validate booking_id format
    booking_id_str = payload.booking_id.strip()
    try:
        obj_id = ObjectId(booking_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking ID format.")

    # 3. Booking must exist
    booking = bookings_collection.find_one({"_id": obj_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # 4. Status must be Completed (Requirement 1)
    if booking.get("status") != "Completed":
        raise HTTPException(
            status_code=400,
            detail="Only completed bookings can be rated and reviewed."
        )

    # 5. Customer authorization (Requirement 8)
    booking_user_email = booking.get("user_email", "").strip().lower()
    customer_email_clean = validate_and_normalize_email(payload.customer_email)

    if customer_email_clean != booking_user_email:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot review another customer's booking."
        )

    if x_user_email and x_user_email.strip().lower() != booking_user_email:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You cannot review another customer's booking."
        )

    # 6. Prevent duplicate reviews (Requirement 5)
    existing_review = reviews_collection.find_one({"booking_id": booking_id_str})
    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="A review has already been submitted for this booking."
        )

    # 7. Insert review document (Requirements 3 & 4)
    now_iso = datetime.now(timezone.utc).isoformat()
    review_doc = {
        "booking_id": booking_id_str,
        "customer_email": customer_email_clean,
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
        "customer_email": customer_email_clean,
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

    



