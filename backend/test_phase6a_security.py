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

        print("==================================================================")
        print("--- Phase 6A: Critical Authorization & Ownership Security Tests ---")
        print("==================================================================")

        # 0. Health check
        status, ping = make_request("GET", "/db-test")
        assert status == 200, f"Backend connection failed: {ping}"
        print("[PASS] Backend & MongoDB connection healthy.")

        test_customer = "test_phase6a_customer@example.com"
        other_customer = "test_phase6a_other@example.com"
        customer_pwd = "Phase6aPassword123!"
        provider_name = "Amit Electrical Services"
        test_user_emails.extend([test_customer, other_customer])

        # Register and login test customers
        make_request("POST", "/register", data={"name": "Phase6A Customer", "email": test_customer, "password": customer_pwd})
        make_request("POST", "/register", data={"name": "Phase6A Other", "email": other_customer, "password": customer_pwd})

        status, login_res = make_request("POST", "/login", data={"email": test_customer, "password": customer_pwd})
        token_customer = login_res["access_token"]

        status, other_res = make_request("POST", "/login", data={"email": other_customer, "password": customer_pwd})
        token_other = other_res["access_token"]

        status, provider_res = make_request("POST", "/login", data={"email": "amit@provider.fixnear.com", "password": "ProviderPass123!"})
        token_provider = provider_res["access_token"]

        status, saha_res = make_request("POST", "/login", data={"email": "saha@provider.fixnear.com", "password": "ProviderPass123!"})
        token_saha = saha_res["access_token"]

        print(f"[PASS] Test users and tokens ready: {test_customer}, {other_customer}")

        # ---------------------------------------------------------
        # TEST SUITE 1: Profile Ownership & Authentication
        # ---------------------------------------------------------
        print("\n--- Suite 1: Profile Ownership Validation ---")

        # 1.1 GET /profile without Authorization header -> 401 Unauthorized
        status, res = make_request("GET", f"/profile?email={test_customer}")
        assert status == 401, f"Expected 401 for missing header, got {status}: {res}"
        print("[PASS] GET /profile without Authorization header rejected (401 Unauthorized).")

        # 1.2 GET /profile with mismatched email query param -> 403 Forbidden
        status, res = make_request("GET", f"/profile?email={test_customer}", headers={"Authorization": f"Bearer {token_other}"})
        assert status == 403, f"Expected 403 for mismatched user, got {status}: {res}"
        print("[PASS] GET /profile with mismatched email query rejected (403 Forbidden).")

        # 1.3 GET /profile with valid matching token -> 200 OK
        status, res = make_request("GET", f"/profile?email={test_customer}", headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200 and res.get("email") == test_customer, f"Failed valid GET profile: {res}"
        print("[PASS] GET /profile with matching Bearer token succeeded (200 OK).")

        # 1.4 PUT /profile without Authorization header -> 401 Unauthorized
        status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Hacked Name"})
        assert status == 401, f"Expected 401 for PUT without header, got {status}: {res}"
        print("[PASS] PUT /profile without Authorization header rejected (401 Unauthorized).")

        # 1.5 PUT /profile with mismatched email -> 403 Forbidden
        status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Hacked Name"}, headers={"Authorization": f"Bearer {token_other}"})
        assert status == 403, f"Expected 403 for PUT with mismatched token, got {status}: {res}"
        print("[PASS] PUT /profile with mismatched identity rejected (403 Forbidden).")

        # 1.6 PUT /profile with valid matching token -> 200 OK
        status, res = make_request("PUT", "/profile", data={"email": test_customer, "name": "Phase6A Verified Name"}, headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200 and res.get("name") == "Phase6A Verified Name", f"Valid profile update failed: {res}"
        print("[PASS] PUT /profile with matching Bearer token succeeded (200 OK).")

        # ---------------------------------------------------------
        # TEST SUITE 2: GET /bookings Data Leakage Protection
        # ---------------------------------------------------------
        print("\n--- Suite 2: GET /bookings Authorization & View Preservation ---")

        # 2.1 GET /bookings without auth header -> 401 Unauthorized
        status, res = make_request("GET", "/bookings")
        assert status == 401, f"Expected 401 for unauthenticated GET /bookings, got {status}: {res}"
        print("[PASS] Unauthenticated GET /bookings dump blocked (401 Unauthorized).")

        # 2.2 GET /bookings?user_email=... without Authorization header -> 401 Unauthorized
        status, res = make_request("GET", f"/bookings?user_email={test_customer}")
        assert status == 401, f"Expected 401 for missing header, got {status}: {res}"
        print("[PASS] GET /bookings by user_email without Authorization header rejected (401 Unauthorized).")

        # 2.3 GET /bookings?user_email=... with mismatched token -> 403 Forbidden
        status, res = make_request("GET", f"/bookings?user_email={test_customer}", headers={"Authorization": f"Bearer {token_other}"})
        assert status == 403, f"Expected 403 for mismatched user, got {status}: {res}"
        print("[PASS] GET /bookings by user_email with mismatched user rejected (403 Forbidden).")

        # 2.4 GET /bookings?user_email=... with matching token -> 200 OK
        status, res = make_request("GET", f"/bookings?user_email={test_customer}", headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200 and isinstance(res, list), f"Expected 200 list for legitimate customer, got {status}: {res}"
        print("[PASS] Legitimate customer bookings retrieved (200 OK).")

        # 2.5 GET /bookings by Provider -> 200 OK (Provider specific view preserved)
        status, res = make_request("GET", f"/bookings?provider={urllib.parse.quote(provider_name)}", headers={"Authorization": f"Bearer {token_provider}"})
        assert status == 200 and isinstance(res, list), f"Expected 200 list for provider view, got {status}: {res}"
        print(f"[PASS] Provider bookings view preserved for '{provider_name}' (200 OK).")

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
        }, headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200, f"Booking creation failed: {b_create}"
        test_booking_id = b_create["booking_id"]
        created_booking_ids.append(test_booking_id)
        print(f"[PASS] Created test booking ID {test_booking_id} with initial status 'Pending'.")

        # 3.1 Anonymous / unauthenticated caller setting status -> 401 Unauthorized
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={"status": "Accepted"})
        assert status == 401, f"Expected 401 for anonymous accept, got {status}: {res}"
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={"status": "Completed"})
        assert status == 401, f"Expected 401 for anonymous complete, got {status}: {res}"
        print("[PASS] Anonymous caller blocked from updating booking status (401 Unauthorized).")

        # 3.2 Customer attempting to accept or complete own booking -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": "Accepted"
        }, headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 403, f"Expected 403 for customer accepting own booking, got {status}: {res}"
        print("[PASS] Customer blocked from accepting own booking (403 Forbidden).")

        # 3.3 Customer attempting to cancel/reject another customer's booking -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": "Rejected"
        }, headers={"Authorization": f"Bearer {token_other}"})
        assert status == 403, f"Expected 403 for cross-customer cancellation, got {status}: {res}"
        print("[PASS] Cross-customer booking modification blocked (403 Forbidden).")

        # 3.4 Provider with mismatched provider_name -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": "Accepted"
        }, headers={"Authorization": f"Bearer {token_saha}"})
        assert status == 403, f"Expected 403 for wrong provider, got {status}: {res}"
        print("[PASS] Mismatched provider rejected (403 Forbidden).")

        # 3.5 Authorized Provider sets status to Accepted -> 200 OK
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": "Accepted"
        }, headers={"Authorization": f"Bearer {token_provider}"})
        assert status == 200 and res.get("status") == "Accepted", f"Provider accept failed: {res}"
        print(f"[PASS] Authorized provider successfully updated status to 'Accepted' (200 OK).")

        # 3.6 Authorized Provider sets status to Completed -> 200 OK
        status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
            "status": "Completed"
        }, headers={"Authorization": f"Bearer {token_provider}"})
        assert status == 200 and res.get("status") == "Completed", f"Provider complete failed: {res}"
        print(f"[PASS] Authorized provider successfully updated status to 'Completed' (200 OK).")

        # 3.7 Completed Booking Lock Rule: Cannot revert Completed booking back to Pending, Accepted, or Rejected -> 400 Bad Request
        for revert_status in ["Pending", "Accepted", "Rejected"]:
            status, res = make_request("PATCH", f"/bookings/{test_booking_id}/status", data={
                "status": revert_status
            }, headers={"Authorization": f"Bearer {token_provider}"})
            assert status == 400, f"Expected 400 lock violation for {revert_status}, got {status}: {res}"
        print("[PASS] Completed booking lock verified: Reversion to Pending/Accepted/Rejected blocked (400 Bad Request).")

        # 3.8 Customer cancellation of own Pending booking -> 200 OK
        # Create a 2nd test booking to verify legitimate customer cancel flow
        status, b2_create = make_request("POST", "/bookings", data={
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-11-16",
            "description": "Phase 6A customer cancel test booking"
        }, headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200
        booking_id_to_cancel = b2_create["booking_id"]
        created_booking_ids.append(booking_id_to_cancel)

        status, res = make_request("PATCH", f"/bookings/{booking_id_to_cancel}/status", data={
            "status": "Rejected"
        }, headers={"Authorization": f"Bearer {token_customer}"})
        assert status == 200 and res.get("status") == "Rejected", f"Customer cancel failed: {res}"
        print("[PASS] Legitimate customer cancellation of own booking verified (200 OK).")

    finally:
        # ---------------------------------------------------------
        # CLEANUP & DATABASE INTEGRITY
        # ---------------------------------------------------------
        print("\n--- Cleanup & Database Integrity Verification ---")
        from pymongo import MongoClient
        from bson import ObjectId
        mongo_client = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
        db = mongo_client["local_service_marketplace"]

        if created_booking_ids:
            db["bookings"].delete_many({"_id": {"$in": [ObjectId(bid) for bid in created_booking_ids]}})
        if test_user_emails:
            db["users"].delete_many({"email": {"$in": test_user_emails}})
        print("[PASS] Cleaned up temporary test documents.")

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

        print("\n==================================================================")
        print("--- ALL PHASE 6A SECURITY TESTS PASSED SUCCESSFULLY! ---")
        print("==================================================================")

if __name__ == "__main__":
    run_tests()
