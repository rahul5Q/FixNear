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
    print("==================================================================")
    print("--- Phase 6A: Critical Authorization & Ownership Security Tests ---")
    print("==================================================================")

    # 0. Health check
    status, ping = make_request("GET", "/db-test")
    assert status == 200, f"Backend connection failed: {ping}"
    print("[PASS] Backend & MongoDB connection healthy.")

    test_customer = "test_phase6a_customer@example.com"
    other_customer = "test_phase6a_other@example.com"
    provider_name = "Amit Electrical Services"

    import os
    from pymongo import MongoClient
    from bson import ObjectId
    mongo_client = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
    db = mongo_client["local_service_marketplace"]

    # Register test customer in DB if not existing
    if not db["users"].find_one({"email": test_customer}):
        db["users"].insert_one({
            "name": "Phase6A Customer",
            "email": test_customer,
            "password": "hashed_test_password"
        })
    print(f"[PASS] Test user ready: {test_customer}")

    # ---------------------------------------------------------
    # TEST SUITE 1: Profile Ownership & X-User-Email Validation
    # ---------------------------------------------------------
    print("\n--- Suite 1: Profile Ownership Validation ---")

    # 1.1 GET /profile without X-User-Email header -> 401 Unauthorized
    status, res = make_request("GET", f"/profile?email={test_customer}")
    assert status == 401, f"Expected 401 for missing header, got {status}: {res}"
    print("[PASS] GET /profile without X-User-Email rejected (401 Unauthorized).")

    # 1.2 GET /profile with mismatched X-User-Email -> 403 Forbidden
    status, res = make_request("GET", f"/profile?email={test_customer}", headers={"X-User-Email": other_customer})
    assert status == 403, f"Expected 403 for mismatched header, got {status}: {res}"
    print("[PASS] GET /profile with mismatched X-User-Email rejected (403 Forbidden).")

    # 1.3 GET /profile with valid matching X-User-Email -> 200 OK
    status, res = make_request("GET", f"/profile?email={test_customer}", headers={"X-User-Email": test_customer})
    assert status == 200 and res.get("email") == test_customer, f"Failed valid GET profile: {res}"
    print("[PASS] GET /profile with matching X-User-Email succeeded (200 OK).")

    # 1.4 PUT /profile without X-User-Email header -> 401 Unauthorized
    status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Hacked Name"})
    assert status == 401, f"Expected 401 for PUT without header, got {status}: {res}"
    print("[PASS] PUT /profile without X-User-Email rejected (401 Unauthorized).")

    # 1.5 PUT /profile with mismatched X-User-Email -> 403 Forbidden
    status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Hacked Name"}, headers={"X-User-Email": other_customer})
    assert status == 403, f"Expected 403 for PUT with mismatched header, got {status}: {res}"
    print("[PASS] PUT /profile with mismatched X-User-Email rejected (403 Forbidden).")

    # 1.6 PUT /profile with valid matching X-User-Email -> 200 OK
    status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Phase6A Verified Name"}, headers={"X-User-Email": test_customer})
    assert status == 200 and res.get("name") == "Phase6A Verified Name", f"Valid profile update failed: {res}"
    print("[PASS] PUT /profile with matching X-User-Email succeeded (200 OK).")

    # ---------------------------------------------------------
    # TEST SUITE 2: GET /bookings Data Leakage Protection
    # ---------------------------------------------------------
    print("\n--- Suite 2: GET /bookings Authorization & View Preservation ---")

    # 2.1 GET /bookings without query params and without auth headers -> 401 Unauthorized
    status, res = make_request("GET", "/bookings")
    assert status == 401, f"Expected 401 for unauthenticated GET /bookings, got {status}: {res}"
    print("[PASS] Unauthenticated GET /bookings dump blocked (401 Unauthorized).")

    # 2.2 GET /bookings?user_email=... without X-User-Email -> 401 Unauthorized
    status, res = make_request("GET", f"/bookings?user_email={test_customer}")
    assert status == 401, f"Expected 401 for missing header, got {status}: {res}"
    print("[PASS] GET /bookings by user_email without X-User-Email rejected (401 Unauthorized).")

    # 2.3 GET /bookings?user_email=... with mismatched X-User-Email -> 403 Forbidden
    status, res = make_request("GET", f"/bookings?user_email={test_customer}", headers={"X-User-Email": other_customer})
    assert status == 403, f"Expected 403 for mismatched header, got {status}: {res}"
    print("[PASS] GET /bookings by user_email with mismatched X-User-Email rejected (403 Forbidden).")

    # 2.4 GET /bookings?user_email=... with matching X-User-Email -> 200 OK
    status, res = make_request("GET", f"/bookings?user_email={test_customer}", headers={"X-User-Email": test_customer})
    assert status == 200 and isinstance(res, list), f"Expected 200 list for legitimate customer, got {status}: {res}"
    print("[PASS] Legitimate customer bookings retrieved (200 OK).")

    # 2.5 GET /bookings?provider=... -> 200 OK (Provider specific view preserved)
    status, res = make_request("GET", f"/bookings?provider={urllib.parse.quote(provider_name)}")
    assert status == 200 and isinstance(res, list), f"Expected 200 list for provider view, got {status}: {res}"
    print(f"[PASS] Provider bookings view preserved for '{provider_name}' (200 OK).")

    # 2.6 GET /bookings with X-Role: provider -> 200 OK (ManageBookings portal all-providers view preserved)
    status, res = make_request("GET", "/bookings", headers={"X-Role": "provider"})
    assert status == 200 and isinstance(res, list), f"Expected 200 for provider portal all view, got {status}: {res}"
    print("[PASS] Provider portal all-providers view preserved (200 OK).")

    # ---------------------------------------------------------
    # TEST SUITE 3: Booking Status Authorization & Lock Protection
    # ---------------------------------------------------------
    print("\n--- Suite 3: Booking Status Authorization & Completed Lock ---")

    # Create a test booking
    status, b_create = make_request("POST", "/bookings", data={
        "user_email": test_customer,
        "service": "Electrician",
        "provider": provider_name,
        "date": "2026-11-15",
        "description": "Phase 6A status test booking"
    })
    assert status == 200, f"Booking creation failed: {b_create}"

    # Fetch booking ID
    status, b_list = make_request("GET", f"/bookings?user_email={test_customer}", headers={"X-User-Email": test_customer})
    assert status == 200 and len(b_list) > 0
    test_booking_id = b_list[-1]["id"]
    print(f"[PASS] Created test booking ID {test_booking_id} with initial status 'Pending'.")

    # 3.1 Anonymous / unauthorized caller setting 'Accepted' or 'Completed' -> 403 Forbidden
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={"status": "Accepted"})
    assert status == 403, f"Expected 403 for anonymous accept, got {status}: {res}"
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={"status": "Completed"})
    assert status == 403, f"Expected 403 for anonymous complete, got {status}: {res}"
    print("[PASS] Anonymous caller blocked from accepting/completing bookings (403 Forbidden).")

    # 3.2 Customer attempting to accept or complete own booking -> 403 Forbidden
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
        "status": "Accepted",
        "role": "customer",
        "updater_email": test_customer
    }, headers={"X-User-Email": test_customer})
    assert status == 403, f"Expected 403 for customer accepting own booking, got {status}: {res}"
    print("[PASS] Customer blocked from accepting own booking (403 Forbidden).")

    # 3.3 Customer attempting to cancel/reject another customer's booking -> 403 Forbidden
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
        "status": "Rejected",
        "role": "customer",
        "updater_email": other_customer
    }, headers={"X-User-Email": other_customer})
    assert status == 403, f"Expected 403 for cross-customer cancellation, got {status}: {res}"
    print("[PASS] Cross-customer booking modification blocked (403 Forbidden).")

    # 3.4 Provider with mismatched provider_name -> 403 Forbidden
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
        "status": "Accepted",
        "role": "provider",
        "provider_name": "Saha Plumbing Services"
    }, headers={"X-Role": "provider"})
    assert status == 403, f"Expected 403 for wrong provider name, got {status}: {res}"
    print("[PASS] Mismatched provider name rejected (403 Forbidden).")

    # 3.5 Authorized Provider sets status to Accepted -> 200 OK
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
        "status": "Accepted",
        "role": "provider",
        "provider_name": provider_name
    }, headers={"X-Role": "provider"})
    assert status == 200 and res.get("status") == "Accepted", f"Provider accept failed: {res}"
    print(f"[PASS] Authorized provider successfully updated status to 'Accepted' (200 OK).")

    # 3.6 Authorized Provider sets status to Completed -> 200 OK
    status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
        "status": "Completed",
        "role": "provider",
        "provider_name": provider_name
    }, headers={"X-Role": "provider"})
    assert status == 200 and res.get("status") == "Completed", f"Provider complete failed: {res}"
    print(f"[PASS] Authorized provider successfully updated status to 'Completed' (200 OK).")

    # 3.7 Completed Booking Lock Rule: Cannot revert Completed booking back to Pending, Accepted, or Rejected -> 400 Bad Request
    for revert_status in ["Pending", "Accepted", "Rejected"]:
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": revert_status,
            "role": "provider",
            "provider_name": provider_name
        }, headers={"X-Role": "provider"})
        assert status == 400, f"Expected 400 lock violation for {revert_status}, got {status}: {res}"
    print("[PASS] Completed booking lock verified: Reversion to Pending/Accepted/Rejected blocked (400 Bad Request).")

    # 3.8 Customer cancellation of own Pending booking -> 200 OK
    # Create a 2nd test booking to verify legitimate customer cancel flow
    make_request("POST", "/bookings", data={
        "user_email": test_customer,
        "service": "Electrician",
        "provider": provider_name,
        "date": "2026-11-16",
        "description": "Phase 6A customer cancel test booking"
    })
    status, b_list = make_request("GET", f"/bookings?user_email={test_customer}", headers={"X-User-Email": test_customer})
    booking_id_to_cancel = b_list[-1]["id"]
    status, res = make_request("PATCH", f"/bookings/{booking_id_to_cancel}/status", data={
        "status": "Rejected",
        "role": "customer",
        "updater_email": test_customer
    }, headers={"X-User-Email": test_customer})
    assert status == 200 and res.get("status") == "Rejected", f"Customer cancel failed: {res}"
    print("[PASS] Legitimate customer cancellation of own booking verified (200 OK).")

    # ---------------------------------------------------------
    # CLEANUP & DATABASE INTEGRITY
    # ---------------------------------------------------------
    print("\n--- Cleanup & Database Integrity Verification ---")
    db["bookings"].delete_many({"_id": {"$in": [ObjectId(test_booking_id), ObjectId(booking_id_to_cancel)]}})
    db["users"].delete_many({"email": test_customer})
    print("[PASS] Cleaned up temporary test documents.")

    collections = db.list_collection_names()
    for col in ["users", "providers", "services", "bookings", "reviews"]:
        assert col in collections, f"Missing collection: {col}"
        count = db[col].count_documents({})
        print(f"[PASS] Collection '{col}' intact with {count} documents.")

    print("\n==================================================================")
    print("--- ALL PHASE 6A SECURITY TESTS PASSED SUCCESSFULLY! ---")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
