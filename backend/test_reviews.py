import json
import urllib.request
import urllib.parse
import urllib.error
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, data=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    if headers is None:
        headers = {}
    
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            status = response.status
            try:
                json_data = json.loads(res_body)
            except Exception:
                json_data = res_body
            return status, json_data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = err_body
        return e.code, err_json

def run_tests():
    print("--- Starting Phase 4 Customer Rating & Review System API Tests ---")
    
    # 0. Test server connectivity
    status, ping = make_request("GET", "/db-test")
    assert status == 200, f"db-test failed with {status}: {ping}"
    print("[PASS] Backend and MongoDB connectivity verified.")

    customer_a = "test_reviewer_a@example.com"
    customer_b = "test_reviewer_b@example.com"
    provider_name = "Test Review Provider"
    
    # 1. Create a test booking
    status, booking_res = make_request("POST", "/bookings", data={
        "user_email": customer_a,
        "service": "Test Cleaning",
        "provider": provider_name,
        "date": "2026-10-30",
        "description": "Test booking for review system"
    })
    assert status == 200, f"Create booking failed: {booking_res}"

    # Fetch created booking id
    status, bookings_list = make_request("GET", f"/bookings?user_email={urllib.parse.quote(customer_a)}", headers={"X-User-Email": customer_a})
    assert status == 200 and len(bookings_list) > 0, "Failed to retrieve created booking"
    booking_id = bookings_list[-1]["id"]
    print(f"[PASS] Created test booking with ID: {booking_id} (Status: Pending)")

    # 2. Test Requirement 1: Rating blocked when status is NOT Completed (currently Pending)
    status, rev_pending = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 5,
        "comment": "Should fail because pending"
    }, headers={"X-User-Email": customer_a})
    assert status == 400, f"Expected 400 for pending booking, got {status}: {rev_pending}"
    assert "Only completed bookings" in str(rev_pending.get("detail", ""))
    print("[PASS] Requirement 1: Review blocked on Pending booking (400 Bad Request).")

    # Update status to Accepted
    status, status_patch = make_request("PATCH", f"/bookings/{booking_id}/status", data={
        "status": "Accepted",
        "role": "provider",
        "provider_name": provider_name
    })
    assert status == 200, f"Update status to Accepted failed: {status_patch}"
    
    # Test review blocked on Accepted booking
    status, rev_accepted = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 5,
        "comment": "Should fail because accepted"
    }, headers={"X-User-Email": customer_a})
    assert status == 400, f"Expected 400 for accepted booking, got {status}: {rev_accepted}"
    print("[PASS] Requirement 1: Review blocked on Accepted booking (400 Bad Request).")

    # Update status to Completed
    status, complete_patch = make_request("PATCH", f"/bookings/{booking_id}/status", data={
        "status": "Completed",
        "role": "provider",
        "provider_name": provider_name
    })
    assert status == 200, f"Update status to Completed failed: {complete_patch}"
    print("[PASS] Updated test booking status to 'Completed'.")

    # 3. Test Requirement 2 & 7: Rating validation (1-5 range)
    # Rating < 1
    status, rev_low = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 0,
        "comment": "Too low"
    }, headers={"X-User-Email": customer_a})
    assert status == 400, f"Expected 400 for rating 0, got {status}: {rev_low}"
    print("[PASS] Requirement 2: Rating < 1 rejected (400 Bad Request).")

    # Rating > 5
    status, rev_high = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 6,
        "comment": "Too high"
    }, headers={"X-User-Email": customer_a})
    assert status == 400, f"Expected 400 for rating 6, got {status}: {rev_high}"
    print("[PASS] Requirement 2: Rating > 5 rejected (400 Bad Request).")

    # 4. Test Requirement 8: Customer Authorization (Customer B cannot review Customer A's booking)
    status, rev_impersonate = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_b,
        "rating": 5,
        "comment": "Impersonator review"
    }, headers={"X-User-Email": customer_b})
    assert status == 403, f"Expected 403 for other customer, got {status}: {rev_impersonate}"
    print("[PASS] Requirement 8: Customer cannot review another customer's booking (403 Forbidden).")

    # 5. Test Valid Review Submission (Requirements 3 & 4)
    status, rev_valid = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 5,
        "comment": "Exceptional service! Very polite and professional."
    }, headers={"X-User-Email": customer_a})
    assert status == 200, f"Expected 200, got {status}: {rev_valid}"
    assert rev_valid["booking_id"] == booking_id
    assert rev_valid["customer_email"] == customer_a
    assert rev_valid["provider"] == provider_name
    assert rev_valid["rating"] == 5
    assert "Exceptional service" in rev_valid["comment"]
    review_id = rev_valid["id"]
    print(f"[PASS] Requirements 3 & 4: Review created successfully with ID {review_id} linked to booking, customer, and provider.")

    # 6. Test Requirement 5: Duplicate Review Prevention
    status, rev_duplicate = make_request("POST", "/reviews", data={
        "booking_id": booking_id,
        "customer_email": customer_a,
        "rating": 4,
        "comment": "Second review attempt"
    }, headers={"X-User-Email": customer_a})
    assert status == 400, f"Expected 400 for duplicate, got {status}: {rev_duplicate}"
    assert "already been submitted" in str(rev_duplicate.get("detail", ""))
    print("[PASS] Requirement 5: Duplicate review for same booking prevented (400 Bad Request).")

    # 7. Test Requirement 6: Display reviews and average calculation via API
    # Create a 2nd completed booking and review for the same provider to test average calculation
    status, booking_res_2 = make_request("POST", "/bookings", data={
        "user_email": customer_b,
        "service": "Test Cleaning",
        "provider": provider_name,
        "date": "2026-10-31",
        "description": "Second test booking"
    })
    status, bookings_b = make_request("GET", f"/bookings?user_email={urllib.parse.quote(customer_b)}", headers={"X-User-Email": customer_b})
    booking_id_2 = bookings_b[-1]["id"]
    make_request("PATCH", f"/bookings/{booking_id_2}/status", data={
        "status": "Completed",
        "role": "provider",
        "provider_name": provider_name
    })
    status, rev_valid_2 = make_request("POST", "/reviews", data={
        "booking_id": booking_id_2,
        "customer_email": customer_b,
        "rating": 3,
        "comment": "Good job, but slightly late."
    }, headers={"X-User-Email": customer_b})
    assert status == 200, f"Second review creation failed: {rev_valid_2}"
    
    # Query GET /reviews?provider=...
    status, p_revs = make_request("GET", f"/reviews?provider={urllib.parse.quote(provider_name)}")
    assert status == 200
    assert len(p_revs) == 2, f"Expected 2 reviews, got {len(p_revs)}"
    print("[PASS] GET /reviews?provider=... returned correct review list.")

    # Query GET /reviews/summary?provider=...
    status, summary = make_request("GET", f"/reviews/summary?provider={urllib.parse.quote(provider_name)}")
    assert status == 200
    assert summary["total_reviews"] == 2
    # Average of 5 and 3 is 4.0
    assert summary["average_rating"] == 4.0, f"Expected average 4.0, got {summary['average_rating']}"
    print(f"[PASS] Requirement 6: Provider review summary computed average rating {summary['average_rating']} across {summary['total_reviews']} reviews.")

    # Query GET /reviews?customer_email=...
    status, c_revs = make_request("GET", f"/reviews?customer_email={urllib.parse.quote(customer_a)}")
    assert status == 200
    assert any(r["booking_id"] == booking_id for r in c_revs)
    print("[PASS] GET /reviews?customer_email=... returned customer reviews.")

    import os
    from pymongo import MongoClient
    from bson import ObjectId
    mongo_client = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
    db = mongo_client["local_service_marketplace"]
    
    db["bookings"].delete_many({"_id": {"$in": [ObjectId(booking_id), ObjectId(booking_id_2)]}})
    db["reviews"].delete_many({"provider": provider_name})
    print("[PASS] Cleaned up temporary test bookings and reviews.")

    # 9. Verify database collections integrity
    collections = db.list_collection_names()
    expected_cols = ["users", "providers", "services", "bookings", "reviews"]
    for col in expected_cols:
        assert col in collections, f"Collection '{col}' missing!"
        count = db[col].count_documents({})
        print(f"[PASS] Collection '{col}' intact with {count} documents.")

    print("\n--- ALL PHASE 4 REVIEW SYSTEM TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    run_tests()
