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

        print("==================================================================")
        print("--- Phase 6B: Validation, Normalization & HTTP Codes Tests ---")
        print("==================================================================")

        # 0. Health check
        status, ping = make_request("GET", "/db-test")
        assert status == 200, f"db-test failed: {ping}"
        print("[PASS] Backend & MongoDB connection healthy.")

        raw_test_email = "  Phase6B_TestUser@Example.COM  "
        normalized_email = "phase6b_testuser@example.com"
        test_user_emails.append(normalized_email)
        provider_name = "Amit Electrical Services"

        # -------------------------------------------------------------
        # SUITE 1: Input Validation Boundaries (Registration)
        # -------------------------------------------------------------
        print("\n--- Suite 1: Registration Validation Boundaries ---")

        # 1.1 Name too short (<2 chars) -> 400
        status, res = make_request("POST", "/register", data={"name": "A", "email": "valid@example.com", "password": "password123"})
        assert status == 400, f"Expected 400 for short name, got {status}: {res}"
        print("[PASS] Name < 2 characters rejected (400 Bad Request).")

        # 1.2 Password too short (<6 chars) -> 400
        status, res = make_request("POST", "/register", data={"name": "Valid Name", "email": "valid@example.com", "password": "123"})
        assert status == 400, f"Expected 400 for short password, got {status}: {res}"
        print("[PASS] Password < 6 characters rejected (400 Bad Request).")

        # 1.3 Password too long (>72 chars) -> 400
        status, res = make_request("POST", "/register", data={"name": "Valid Name", "email": "valid@example.com", "password": "A" * 73})
        assert status == 400, f"Expected 400 for password > 72 chars, got {status}: {res}"
        print("[PASS] Password > 72 characters rejected (400 Bad Request).")

        # 1.4 Invalid email formats -> 400
        for bad_email in ["notanemail", "plainaddress", "user@.com", "@domain.com", ""]:
            status, res = make_request("POST", "/register", data={"name": "Valid Name", "email": bad_email, "password": "password123"})
            assert status == 400, f"Expected 400 for invalid email '{bad_email}', got {status}: {res}"
        print("[PASS] Invalid email formats rejected (400 Bad Request).")

        # -------------------------------------------------------------
        # SUITE 2: Registration, Normalization & HTTP 409 Conflict
        # -------------------------------------------------------------
        print("\n--- Suite 2: Registration Normalization & HTTP 409 ---")

        # 2.1 Valid registration with raw mixed-case and spaces -> 200 OK
        status, res = make_request("POST", "/register", data={"name": "  Phase 6B User  ", "email": raw_test_email, "password": "securepassword123"})
        assert status == 200 and res.get("message") == "Registration successful", f"Registration failed: {res}"
        print("[PASS] Registration with mixed-case and spaces succeeded (200 OK).")

        # 2.2 Duplicate email registration -> HTTP 409 Conflict
        status, res = make_request("POST", "/register", data={"name": "Duplicate User", "email": normalized_email, "password": "anotherpassword123"})
        assert status == 409, f"Expected 409 for duplicate email, got {status}: {res}"
        assert "Email already registered" in str(res.get("detail", ""))
        print("[PASS] Duplicate registration returned HTTP 409 Conflict.")

        # 2.3 Duplicate registration with varied casing/spaces -> HTTP 409 Conflict
        status, res = make_request("POST", "/register", data={"name": "Duplicate User", "email": "  PHASE6B_TESTUSER@EXAMPLE.COM  ", "password": "anotherpassword123"})
        assert status == 409, f"Expected 409 for case-varied duplicate, got {status}: {res}"
        print("[PASS] Case-insensitive duplicate registration returned HTTP 409 Conflict.")

        # -------------------------------------------------------------
        # SUITE 3: Login Authentication & HTTP 401 Unauthorized
        # -------------------------------------------------------------
        print("\n--- Suite 3: Login Normalization & HTTP 401 ---")

        # 3.1 Invalid password -> HTTP 401 Unauthorized
        status, res = make_request("POST", "/login", data={"email": normalized_email, "password": "wrongpassword"})
        assert status == 401, f"Expected 401 for wrong password, got {status}: {res}"
        assert "Invalid email or password" in str(res.get("detail", ""))
        print("[PASS] Invalid password returned HTTP 401 Unauthorized.")

        # 3.2 Non-existent email -> HTTP 401 Unauthorized
        status, res = make_request("POST", "/login", data={"email": "nonexistent@example.com", "password": "anyPassword123"})
        assert status == 401, f"Expected 401 for non-existent email, got {status}: {res}"
        print("[PASS] Non-existent email login returned HTTP 401 Unauthorized.")

        # 3.3 Successful login with raw mixed-case/spaces email -> 200 OK & normalized email returned
        status, res = make_request("POST", "/login", data={"email": "  PHASE6B_TESTUSER@EXAMPLE.COM  ", "password": "securepassword123"})
        assert status == 200 and res.get("email") == normalized_email, f"Login failed: {res}"
        user_token = res.get("access_token")
        assert user_token is not None, "Login did not return access_token"
        print("[PASS] Login with mixed-case/spaces email succeeded (200 OK) and returned normalized email & JWT.")

        # Authenticate provider Amit for provider operations
        status, p_res = make_request("POST", "/login", data={"email": "amit@provider.fixnear.com", "password": "ProviderPass123!"})
        assert status == 200 and "access_token" in p_res, f"Provider login failed: {p_res}"
        provider_token = p_res["access_token"]

        # -------------------------------------------------------------
        # SUITE 4: Profile Operations with Email Normalization
        # -------------------------------------------------------------
        print("\n--- Suite 4: Profile Operations Normalization ---")

        # 4.1 GET /profile with mixed-case and matching header -> 200 OK
        quoted_email = urllib.parse.quote(raw_test_email)
        status, res = make_request("GET", f"/profile?email={quoted_email}", headers={"Authorization": f"Bearer {user_token}"})
        assert status == 200 and res.get("email") == normalized_email, f"GET profile failed: {res}"
        print("[PASS] GET /profile normalized email lookup succeeded (200 OK).")

        # 4.2 PUT /profile updating name -> 200 OK
        status, res = make_request("PUT", "/profile", data={"email": raw_test_email, "name": "Updated 6B Name"}, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 200 and res.get("name") == "Updated 6B Name", f"PUT profile failed: {res}"
        print("[PASS] PUT /profile with normalized email succeeded (200 OK).")

        # -------------------------------------------------------------
        # SUITE 5: Booking Inputs Validation & Email Normalization
        # -------------------------------------------------------------
        print("\n--- Suite 5: Booking Inputs Validation & Normalization ---")

        # 5.1 Invalid date format -> 400
        status, res = make_request("POST", "/bookings", data={
            "user_email": normalized_email,
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026/11/25",
            "description": "Short circuit problem"
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 400, f"Expected 400 for bad date format, got {status}: {res}"
        print("[PASS] Booking with invalid date format rejected (400 Bad Request).")

        # 5.2 Description too short (<3 chars) -> 400
        status, res = make_request("POST", "/bookings", data={
            "user_email": normalized_email,
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-11-25",
            "description": "No"
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 400, f"Expected 400 for short description, got {status}: {res}"
        print("[PASS] Booking with description < 3 chars rejected (400 Bad Request).")

        # 5.3 Description too long (>1000 chars) -> 400
        status, res = make_request("POST", "/bookings", data={
            "user_email": normalized_email,
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-11-25",
            "description": "A" * 1001
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 400, f"Expected 400 for description > 1000 chars, got {status}: {res}"
        print("[PASS] Booking with description > 1000 chars rejected (400 Bad Request).")

        # 5.4 Valid booking with mixed case email -> 200 OK & normalized in DB
        status, res = make_request("POST", "/bookings", data={
            "user_email": raw_test_email,
            "service": "Electrician",
            "provider": provider_name,
            "date": "2026-11-25",
            "description": "Fan making noise and not rotating properly"
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 200 and "booking_id" in res, f"Valid booking creation failed: {res}"
        b_id = res["booking_id"]
        created_booking_ids.append(b_id)
        print(f"[PASS] Valid booking created with normalized email (ID: {b_id}).")

        # 5.5 Query bookings by mixed-case email -> 200 OK
        status, b_list = make_request("GET", f"/bookings?user_email={urllib.parse.quote('  PHASE6B_TESTUSER@EXAMPLE.COM  ')}", headers={"Authorization": f"Bearer {user_token}"})
        assert status == 200 and len(b_list) > 0, f"Booking lookup failed: {b_list}"
        assert b_list[0]["user_email"] == normalized_email
        print("[PASS] GET /bookings with mixed-case email retrieved normalized records.")

        # -------------------------------------------------------------
        # SUITE 6: Review Comment Validation & Normalization
        # -------------------------------------------------------------
        print("\n--- Suite 6: Review Validation & Completed Lock ---")

        # Update booking to Completed by provider
        status, res = make_request("PATCH", f"/bookings/{b_id}/status", data={
            "status": "Completed"
        }, headers={"Authorization": f"Bearer {provider_token}"})
        assert status == 200, f"Provider status update failed: {res}"
        print("[PASS] Booking marked as 'Completed'.")

        # 6.1 Review comment too long (>1000 chars) -> 400 Bad Request
        status, res = make_request("POST", "/reviews", data={
            "booking_id": b_id,
            "rating": 5,
            "comment": "A" * 1001
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 400, f"Expected 400 for comment > 1000 chars, got {status}: {res}"
        assert "cannot exceed 1000 characters" in str(res.get("detail", ""))
        print("[PASS] Review comment > 1000 characters rejected (400 Bad Request).")

        # 6.2 Legitimate review with mixed case email -> 200 OK
        status, res = make_request("POST", "/reviews", data={
            "booking_id": b_id,
            "rating": 5,
            "comment": "Quick and polite professional!"
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert status == 200 and res.get("customer_email") == normalized_email, f"Review submission failed: {res}"
        print("[PASS] Legitimate review submitted with normalized email.")

        # 6.3 Verify Completed Booking Final Lock
        status, res = make_request("PATCH", f"/bookings/{b_id}/status", data={
            "status": "Pending"
        }, headers={"Authorization": f"Bearer {provider_token}"})
        assert status == 400, f"Expected 400 lock violation, got {status}: {res}"
        print("[PASS] Completed booking final lock preserved (400 Bad Request).")

    finally:
        # Cleanup test records directly via MongoDB
        print("\n--- Cleaning Up Phase 6B Test Records ---")
        from pymongo import MongoClient
        from bson import ObjectId
        c = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
        db = c["local_service_marketplace"]

        if created_booking_ids:
            db["bookings"].delete_many({"_id": {"$in": [ObjectId(bid) for bid in created_booking_ids]}})
            db["reviews"].delete_many({"booking_id": {"$in": created_booking_ids}})
            print(f"[PASS] Removed {len(created_booking_ids)} test bookings & reviews.")

        if test_user_emails:
            db["users"].delete_many({"email": {"$in": test_user_emails}})
            print(f"[PASS] Removed test user accounts: {test_user_emails}")

        # Verify DB integrity: assert collection counts match baseline state before test
        expected_counts = initial_counts or {'services': 6, 'users': 4, 'providers': 3, 'reviews': 1, 'bookings': 13}
        for col, exp in expected_counts.items():
            actual = db[col].count_documents({})
            assert actual == exp, f"DB count mismatch for {col}: expected {exp}, got {actual}"
            print(f"[PASS] Collection '{col}' intact ({actual} documents).")

        # Shutdown test process if started by this script
        if server_process is not None:
            print("[INFO] Terminating controlled Uvicorn test process...")
            server_process.terminate()
            server_process.wait()
            print("[PASS] Uvicorn test process terminated cleanly.")

    print("\n==================================================================")
    print("--- ALL PHASE 6B TESTS PASSED SUCCESSFULLY! ---")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
