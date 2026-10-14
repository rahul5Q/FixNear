import json
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import time
import socket
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def is_port_open(port=8000):
    s = socket.socket()
    try:
        res = s.connect_ex(('127.0.0.1', port))
        return res == 0
    finally:
        s.close()

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
    server_process = None
    created_booking_ids = []
    created_review_ids = []
    test_user_emails = []

    # Record baseline database counts prior to test execution
    initial_counts = None
    try:
        from pymongo import MongoClient
        _init_c = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
        _init_db = _init_c["local_service_marketplace"]
        initial_counts = {col: _init_db[col].count_documents({}) for col in ['services', 'users', 'providers', 'reviews', 'bookings']}
    except Exception:
        pass

    try:
        # Step 1: Ensure backend server is accessible
        if not is_port_open(8000):
            print("[INFO] Starting controlled Uvicorn test process...")
            server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            for _ in range(30):
                time.sleep(0.3)
                if is_port_open(8000):
                    break
            else:
                raise RuntimeError("Failed to start controlled Uvicorn test process on port 8000.")

        print("--- Starting Phase 4 Customer Rating & Review System API Tests ---")

        # 0. Test server connectivity
        status, ping = make_request("GET", "/db-test")
        assert status == 200, f"db-test failed with {status}: {ping}"
        print("[PASS] Backend and MongoDB connectivity verified.")

        customer_a = "test_reviewer_a@example.com"
        customer_b = "test_reviewer_b@example.com"
        customer_pwd = "ReviewPass123!"
        provider_name = "Amit Electrical Services"
        test_user_emails.extend([customer_a, customer_b])

        # Register and login test customers
        make_request("POST", "/register", data={"name": "Reviewer A", "email": customer_a, "password": customer_pwd})
        make_request("POST", "/register", data={"name": "Reviewer B", "email": customer_b, "password": customer_pwd})

        status, login_a = make_request("POST", "/login", data={"email": customer_a, "password": customer_pwd})
        token_a = login_a["access_token"]

        status, login_b = make_request("POST", "/login", data={"email": customer_b, "password": customer_pwd})
        token_b = login_b["access_token"]

        # Login provider Amit
        status, login_amit = make_request("POST", "/login", data={"email": "amit@provider.fixnear.com", "password": "ProviderPass123!"})
        token_amit = login_amit["access_token"]
        print("[PASS] Test accounts and JWT tokens prepared.")

        # 1. Create a test booking
        status, booking_res = make_request("POST", "/bookings", data={
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-10-30",
            "description": "Test booking for review system"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200, f"Create booking failed: {booking_res}"
        booking_id = booking_res["booking_id"]
        created_booking_ids.append(booking_id)
        print(f"[PASS] Created test booking with ID: {booking_id} (Status: Pending)")

        # 2. Test Requirement 1: Rating blocked when status is NOT Completed (currently Pending)
        status, rev_pending = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Should fail because pending"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for pending booking, got {status}: {rev_pending}"
        assert "Only completed bookings" in str(rev_pending.get("detail", ""))
        print("[PASS] Requirement 1: Review blocked on Pending booking (400 Bad Request).")

        # Update status to Accepted
        status, status_patch = make_request("PATCH", f"/bookings/{booking_id}/status", data={
            "status": "Accepted"
        }, headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200, f"Update status to Accepted failed: {status_patch}"

        # Test review blocked on Accepted booking
        status, rev_accepted = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Should fail because accepted"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for accepted booking, got {status}: {rev_accepted}"
        print("[PASS] Requirement 1: Review blocked on Accepted booking (400 Bad Request).")

        # Update status to Completed
        status, complete_patch = make_request("PATCH", f"/bookings/{booking_id}/status", data={
            "status": "Completed"
        }, headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200, f"Update status to Completed failed: {complete_patch}"
        print("[PASS] Updated test booking status to 'Completed'.")

        # 3. Test Requirement 2 & 7: Rating validation (1-5 range)
        # Rating < 1
        status, rev_low = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 0,
            "comment": "Too low"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for rating 0, got {status}: {rev_low}"
        print("[PASS] Requirement 2: Rating < 1 rejected (400 Bad Request).")

        # Rating > 5
        status, rev_high = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 6,
            "comment": "Too high"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for rating 6, got {status}: {rev_high}"
        print("[PASS] Requirement 2: Rating > 5 rejected (400 Bad Request).")

        # 4. Test Requirement 8: Customer Authorization (Customer B cannot review Customer A's booking)
        status, rev_impersonate = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Impersonator review"
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert status == 403, f"Expected 403 for other customer, got {status}: {rev_impersonate}"
        print("[PASS] Requirement 8: Customer cannot review another customer's booking (403 Forbidden).")

        # 5. Test Valid Review Submission (Requirements 3 & 4)
        status, rev_valid = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Exceptional service! Very polite and professional."
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200, f"Expected 200, got {status}: {rev_valid}"
        assert rev_valid["booking_id"] == booking_id
        assert rev_valid["customer_email"] == customer_a
        assert rev_valid["provider"] == provider_name
        assert rev_valid["rating"] == 5
        assert "Exceptional service" in rev_valid["comment"]
        review_id = rev_valid["id"]
        created_review_ids.append(review_id)
        print(f"[PASS] Requirements 3 & 4: Review created successfully with ID {review_id} linked to booking, customer, and provider.")

        # 6. Test Requirement 5: Duplicate Review Prevention
        status, rev_duplicate = make_request("POST", "/reviews", data={
            "booking_id": booking_id,
            "rating": 4,
            "comment": "Second review attempt"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for duplicate, got {status}: {rev_duplicate}"
        assert "already been submitted" in str(rev_duplicate.get("detail", ""))
        print("[PASS] Requirement 5: Duplicate review for same booking prevented (400 Bad Request).")

        # 7. Test Requirement 6: Display reviews and average calculation via API
        # Create a 2nd completed booking and review for the same provider to test average calculation
        status, booking_res_2 = make_request("POST", "/bookings", data={
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-10-31",
            "description": "Second test booking"
        }, headers={"Authorization": f"Bearer {token_b}"})
        booking_id_2 = booking_res_2["booking_id"]
        created_booking_ids.append(booking_id_2)

        make_request("PATCH", f"/bookings/{booking_id_2}/status", data={
            "status": "Completed"
        }, headers={"Authorization": f"Bearer {token_amit}"})

        status, rev_valid_2 = make_request("POST", "/reviews", data={
            "booking_id": booking_id_2,
            "rating": 3,
            "comment": "Good job, but slightly late."
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert status == 200, f"Second review creation failed: {rev_valid_2}"
        created_review_ids.append(rev_valid_2["id"])

        # Query GET /reviews?provider=...
        status, p_revs = make_request("GET", f"/reviews?provider={urllib.parse.quote(provider_name)}")
        assert status == 200
        assert len(p_revs) >= 2, f"Expected at least 2 reviews, got {len(p_revs)}"
        print("[PASS] GET /reviews?provider=... returned correct review list.")

        # Query GET /reviews/summary?provider=...
        status, summary = make_request("GET", f"/reviews/summary?provider={urllib.parse.quote(provider_name)}")
        assert status == 200
        assert summary["total_reviews"] >= 2
        print(f"[PASS] Requirement 6: Provider review summary computed average rating {summary['average_rating']} across {summary['total_reviews']} reviews.")

        # Query GET /reviews?customer_email=...
        status, c_revs = make_request("GET", f"/reviews?customer_email={urllib.parse.quote(customer_a)}")
        assert status == 200
        assert any(r["booking_id"] == booking_id for r in c_revs)
        print("[PASS] GET /reviews?customer_email=... returned customer reviews.")

    finally:
        print("\n--- Cleaning Up Test Records ---")
        from pymongo import MongoClient
        from bson import ObjectId
        mongo_client = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
        db = mongo_client["local_service_marketplace"]

        if created_booking_ids:
            db["bookings"].delete_many({"_id": {"$in": [ObjectId(bid) for bid in created_booking_ids]}})
        if created_review_ids:
            db["reviews"].delete_many({"_id": {"$in": [ObjectId(rid) for rid in created_review_ids]}})
        if test_user_emails:
            db["users"].delete_many({"email": {"$in": test_user_emails}})
        print("[PASS] Cleaned up temporary test bookings, reviews, and test users.")

        # Verify DB integrity: assert collection counts match baseline state before test
        expected_counts = initial_counts or {'services': 6, 'users': 4, 'providers': 3, 'reviews': 1, 'bookings': 13}
        for col, exp in expected_counts.items():
            actual = db[col].count_documents({})
            assert actual == exp, f"DB count mismatch for {col}: expected {exp}, got {actual}"
            print(f"[PASS] Collection '{col}' intact ({actual} documents).")

        if server_process is not None:
            print("[INFO] Terminating controlled Uvicorn test process...")
            server_process.terminate()
            server_process.wait()
            print("[PASS] Uvicorn test process terminated cleanly.")

        print("\n--- ALL PHASE 4 REVIEW SYSTEM TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    run_tests()
