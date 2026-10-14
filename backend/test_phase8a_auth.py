import json
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import time
import socket
import sys
import os
from datetime import datetime, timedelta, timezone

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

def test_production_secret_validation():
    print("\n--- Suite 0: Production Configuration Validation & Fail-Safe ---")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import main

    orig_env = os.environ.get("APP_ENV")
    orig_secret = os.environ.get("JWT_SECRET")
    orig_invite = os.environ.get("PROVIDER_INVITE_SECRET")
    orig_cors = os.environ.get("CORS_ORIGINS")
    orig_mongo = os.environ.get("MONGO_URI")

    test_exc = None
    try:
        # Enable production mode for tests
        os.environ["APP_ENV"] = "production"
        main.IS_PRODUCTION = True

        # 0.1 JWT_SECRET validation
        if "JWT_SECRET" in os.environ:
            del os.environ["JWT_SECRET"]
        failed = False
        try:
            main.get_validated_jwt_secret()
        except RuntimeError as e:
            failed = True
            assert "JWT_SECRET must be set via environment variable" in str(e)
        assert failed, "Failed to reject missing JWT_SECRET in production mode!"
        print("[PASS] Missing JWT_SECRET in production mode fails startup with RuntimeError.")

        os.environ["JWT_SECRET"] = main.DEV_JWT_SECRET_FALLBACK
        failed = False
        try:
            main.get_validated_jwt_secret()
        except RuntimeError as e:
            failed = True
            assert "insecure development JWT_SECRET fallback cannot be used" in str(e)
        assert failed, "Failed to reject dev fallback JWT_SECRET in production mode!"
        print("[PASS] Insecure dev fallback secret in production mode fails startup with RuntimeError.")

        os.environ["JWT_SECRET"] = "short-secret-key-too-short"
        failed = False
        try:
            main.get_validated_jwt_secret()
        except RuntimeError as e:
            failed = True
            assert "at least 32 characters long" in str(e)
        assert failed, "Failed to reject short secret in production mode!"
        print("[PASS] Secret < 32 characters in production mode fails startup with RuntimeError.")

        strong_prod_key = "production-cryptographically-secure-key-2026-fixnear"
        os.environ["JWT_SECRET"] = strong_prod_key
        validated = main.get_validated_jwt_secret()
        assert validated == strong_prod_key
        print("[PASS] Cryptographically strong secret in production mode accepted.")

        # 0.2 PROVIDER_INVITE_SECRET validation
        if "PROVIDER_INVITE_SECRET" in os.environ:
            del os.environ["PROVIDER_INVITE_SECRET"]
        failed = False
        try:
            main.get_validated_provider_invite_secret()
        except RuntimeError as e:
            failed = True
            assert "PROVIDER_INVITE_SECRET must be set via environment variable" in str(e)
        assert failed, "Failed to reject missing PROVIDER_INVITE_SECRET in production mode!"
        print("[PASS] Missing PROVIDER_INVITE_SECRET in production mode fails startup with RuntimeError.")

        os.environ["PROVIDER_INVITE_SECRET"] = main.DEV_PROVIDER_INVITE_SECRET_FALLBACK
        failed = False
        try:
            main.get_validated_provider_invite_secret()
        except RuntimeError as e:
            failed = True
            assert "insecure development PROVIDER_INVITE_SECRET fallback cannot be used" in str(e)
        assert failed, "Failed to reject dev fallback invite secret in production mode!"
        print("[PASS] Insecure dev fallback invite secret in production mode fails startup with RuntimeError.")

        os.environ["PROVIDER_INVITE_SECRET"] = "short-code"
        failed = False
        try:
            main.get_validated_provider_invite_secret()
        except RuntimeError as e:
            failed = True
            assert "at least 16 characters long" in str(e)
        assert failed, "Failed to reject short invite secret in production mode!"
        print("[PASS] Invite secret < 16 characters in production mode fails startup with RuntimeError.")

        valid_invite = "secure-provider-invite-passcode-2026"
        os.environ["PROVIDER_INVITE_SECRET"] = valid_invite
        assert main.get_validated_provider_invite_secret() == valid_invite
        print("[PASS] Valid provider invite secret in production mode accepted.")

        # 0.3 CORS_ORIGINS validation
        if "CORS_ORIGINS" in os.environ:
            del os.environ["CORS_ORIGINS"]
        failed = False
        try:
            main.get_cors_origins()
        except RuntimeError as e:
            failed = True
            assert "CORS_ORIGINS must be set via environment variable" in str(e)
        assert failed, "Failed to reject missing CORS_ORIGINS in production mode!"
        print("[PASS] Missing CORS_ORIGINS in production mode fails startup with RuntimeError.")

        os.environ["CORS_ORIGINS"] = "*"
        failed = False
        try:
            main.get_cors_origins()
        except RuntimeError as e:
            failed = True
            assert "Wildcard origin '*' is not allowed" in str(e)
        assert failed, "Failed to reject wildcard '*' in CORS_ORIGINS!"
        print("[PASS] Wildcard '*' CORS origin rejected with RuntimeError.")

        os.environ["CORS_ORIGINS"] = "https://fixnear.example.com, https://app.fixnear.com"
        parsed_cors = main.get_cors_origins()
        assert parsed_cors == ["https://fixnear.example.com", "https://app.fixnear.com"]
        print("[PASS] Exact production CORS origins parsed successfully.")

        # 0.4 MONGO_URI validation
        if "MONGO_URI" in os.environ:
            del os.environ["MONGO_URI"]
        failed = False
        try:
            main.get_validated_mongo_uri()
        except RuntimeError as e:
            failed = True
            assert "MONGO_URI must be set via environment variable" in str(e)
        assert failed, "Failed to reject missing MONGO_URI in production mode!"
        print("[PASS] Missing MONGO_URI in production mode fails startup with RuntimeError.")

        prod_mongo = "mongodb://localhost:27017/"
        os.environ["MONGO_URI"] = prod_mongo
        assert main.get_validated_mongo_uri() == prod_mongo
        print("[PASS] Valid MONGO_URI in production mode accepted.")

        # 0.5 Combined validate_production_configuration
        prod_cfg = main.validate_production_configuration()
        assert prod_cfg["jwt_secret"] == strong_prod_key
        assert prod_cfg["provider_invite_secret"] == valid_invite
        assert prod_cfg["cors_origins"] == ["https://fixnear.example.com", "https://app.fixnear.com"]
        assert prod_cfg["mongo_uri"] == prod_mongo
        print("[PASS] Combined validate_production_configuration succeeds when all required settings are valid.")

    except BaseException as exc:
        test_exc = exc
        raise
    finally:
        # Restore original environment
        env_vars = {
            "APP_ENV": orig_env,
            "JWT_SECRET": orig_secret,
            "PROVIDER_INVITE_SECRET": orig_invite,
            "CORS_ORIGINS": orig_cors,
            "MONGO_URI": orig_mongo
        }
        for k, v in env_vars.items():
            if v is not None:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

        try:
            main.IS_PRODUCTION = (os.environ.get("APP_ENV", "development").strip().lower() in ["production", "prod"])
            main.JWT_SECRET = main.get_validated_jwt_secret()
            main.PROVIDER_INVITE_SECRET = main.get_validated_provider_invite_secret()
            main.CORS_ORIGINS = main.get_cors_origins()
            main.MONGO_URI = main.get_validated_mongo_uri()
        except Exception as restore_err:
            print(f"[WARN] Failed to re-validate main configuration during teardown: {restore_err}", file=sys.stderr)
            if test_exc is None:
                raise

def run_tests():
    server_process = None
    created_booking_ids = []
    created_review_ids = []
    test_user_emails = []

    # Capture initial collection counts snapshot before any test creates or deletes database records
    try:
        from pymongo import MongoClient
        _init_c = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        _init_c.admin.command("ping")
        _init_db = _init_c["local_service_marketplace"]
        initial_counts = {col: _init_db[col].count_documents({}) for col in ['services', 'users', 'providers', 'reviews', 'bookings']}
    except Exception as e:
        raise RuntimeError(f"FATAL: Failed to capture initial MongoDB collection baseline counts prior to test execution: {e}. Aborting tests to protect database integrity.")

    try:
        # Run in-process configuration unit tests first
        test_production_secret_validation()

        # Ensure backend server is accessible
        if not is_port_open(8000):
            print("\n[INFO] Starting controlled Uvicorn test process...")
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
        print("--- Phase 8A: Secure JWT Authentication & Authorization Tests ---")
        print("==================================================================")

        # 0. Health check
        status, ping = make_request("GET", "/db-test")
        assert status == 200, f"db-test failed: {ping}"
        print("[PASS] Backend & MongoDB connection healthy.")

        import jwt
        jwt_secret = os.getenv("JWT_SECRET") or "fixnear-local-dev-jwt-secret-do-not-use-in-production-2026"
        jwt_algorithm = "HS256"

        customer_a_email = "phase8a_customer_a@example.com"
        customer_b_email = "phase8a_customer_b@example.com"
        customer_password = "SecurePassword123!"
        test_user_emails.extend([customer_a_email, customer_b_email])

        # Register Customer A & Customer B
        status, res = make_request("POST", "/register", data={
            "name": "Phase8A Customer A",
            "email": customer_a_email,
            "password": customer_password
        })
        assert status == 200, f"Customer A registration failed: {res}"

        status, res = make_request("POST", "/register", data={
            "name": "Phase8A Customer B",
            "email": customer_b_email,
            "password": customer_password
        })
        assert status == 200, f"Customer B registration failed: {res}"
        print("[PASS] Customer test accounts registered successfully.")

        # -------------------------------------------------------------
        # SUITE 1: Provider Self-Registration Restrictions
        # -------------------------------------------------------------
        print("\n--- Suite 1: Provider Self-Registration Security Restrictions ---")

        # 1.1 Customer cannot register as provider without invite code -> 403 Forbidden
        status, res = make_request("POST", "/register", data={
            "name": "Attacker Trying Provider",
            "email": "attacker_provider@example.com",
            "password": "Password123!",
            "role": "provider",
            "provider_name": "Rogue Provider Business"
        })
        assert status == 403, f"Expected 403 for unauthorized provider registration, got {status}: {res}"
        assert "Provider self-registration is restricted" in str(res.get("detail", ""))
        print("[PASS] Provider self-registration without invite code blocked (403 Forbidden).")

        # 1.2 Customer cannot register as provider with invalid invite code -> 403 Forbidden
        status, res = make_request("POST", "/register", data={
            "name": "Attacker Trying Provider",
            "email": "attacker_provider@example.com",
            "password": "Password123!",
            "role": "provider",
            "provider_name": "Rogue Provider Business",
            "provider_invite_code": "wrong-invite-code-12345"
        })
        assert status == 403, f"Expected 403 for invalid invite code, got {status}: {res}"
        print("[PASS] Provider registration with invalid invite code rejected (403 Forbidden).")

        # 1.3 Provider registration with valid invite code succeeds -> 200 OK
        valid_invite = os.getenv("PROVIDER_INVITE_SECRET", "fixnear-provider-invite-2026")
        legit_provider_email = "legit_new_provider@example.com"
        test_user_emails.append(legit_provider_email)
        status, res = make_request("POST", "/register", data={
            "name": "Authorized Electrician",
            "email": legit_provider_email,
            "password": "ProviderSecurePass123!",
            "role": "provider",
            "provider_name": "Authorized Electrician Co",
            "provider_invite_code": valid_invite
        })
        assert status == 200 and res.get("role") == "provider", f"Authorized provider registration failed: {res}"
        print("[PASS] Authorized provider registration with valid invite code succeeded (200 OK).")

        # Login Customer A
        status, login_a = make_request("POST", "/login", data={
            "email": customer_a_email,
            "password": customer_password
        })
        assert status == 200 and "access_token" in login_a, f"Customer A login failed: {login_a}"
        token_a = login_a["access_token"]
        assert login_a["role"] == "customer"
        print("[PASS] Customer A login succeeded with JWT token issued.")

        # Login Customer B
        status, login_b = make_request("POST", "/login", data={
            "email": customer_b_email,
            "password": customer_password
        })
        assert status == 200 and "access_token" in login_b, f"Customer B login failed: {login_b}"
        token_b = login_b["access_token"]
        print("[PASS] Customer B login succeeded with JWT token issued.")

        # Login Default Provider: Amit Electrical Services
        status, login_amit = make_request("POST", "/login", data={
            "email": "amit@provider.fixnear.com",
            "password": "ProviderPass123!"
        })
        assert status == 200 and "access_token" in login_amit, f"Provider Amit login failed: {login_amit}"
        token_amit = login_amit["access_token"]
        assert login_amit["role"] == "provider"
        assert login_amit["provider_name"] == "Amit Electrical Services"
        print("[PASS] Provider Amit logged in with verified role 'provider' and provider_name.")

        # Login Default Provider: Saha Plumbing Services
        status, login_saha = make_request("POST", "/login", data={
            "email": "saha@provider.fixnear.com",
            "password": "ProviderPass123!"
        })
        assert status == 200 and "access_token" in login_saha, f"Provider Saha login failed: {login_saha}"
        token_saha = login_saha["access_token"]
        assert login_saha["role"] == "provider"
        assert login_saha["provider_name"] == "Saha Plumbing Services"
        print("[PASS] Provider Saha logged in with verified role 'provider' and provider_name.")

        # -------------------------------------------------------------
        # SUITE 2: Token Verification & Cryptographic Boundaries
        # -------------------------------------------------------------
        print("\n--- Suite 2: Token Verification Boundaries & Claims ---")

        # 2.1 Verify token claims contain iat and exp
        decoded_claims = jwt.decode(token_a, jwt_secret, algorithms=[jwt_algorithm])
        assert "iat" in decoded_claims, "Token missing 'iat' claim"
        assert "exp" in decoded_claims, "Token missing 'exp' claim"
        print("[PASS] Token verified to include standard 'iat' and 'exp' claims.")

        # 2.2 Missing Authorization header -> 401 Unauthorized
        for endpoint, method in [("/profile", "GET"), ("/bookings", "GET")]:
            status, res = make_request(method, endpoint)
            assert status == 401, f"Expected 401 for missing header on {endpoint}, got {status}: {res}"
            assert "Authorization header is missing" in str(res.get("detail", ""))
        print("[PASS] Missing Authorization header returns 401 Unauthorized.")

        # 2.3 Malformed Authorization header format -> 401 Unauthorized
        for bad_header in ["Token " + token_a, "Bearer", "Bearer token1 token2", token_a]:
            status, res = make_request("GET", "/profile", headers={"Authorization": bad_header})
            assert status == 401, f"Expected 401 for bad format '{bad_header}', got {status}: {res}"
        print("[PASS] Malformed Authorization headers rejected (401 Unauthorized).")

        # 2.4 Forged / Tampered token (signed with wrong secret) -> 401 Unauthorized
        forged_token = jwt.encode(
            {"sub": customer_a_email, "name": "Fake", "role": "customer", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key-attacker-at-least-32-bytes-long",
            algorithm=jwt_algorithm
        )
        status, res = make_request("GET", "/profile", headers={"Authorization": f"Bearer {forged_token}"})
        assert status == 401, f"Expected 401 for forged token, got {status}: {res}"
        print("[PASS] Forged / tampered token rejected (401 Unauthorized).")

        # 2.5 Expired token -> 401 Unauthorized
        expired_token = jwt.encode(
            {"sub": customer_a_email, "name": "Customer A", "role": "customer", "exp": datetime.now(timezone.utc) - timedelta(minutes=10)},
            jwt_secret,
            algorithm=jwt_algorithm
        )
        status, res = make_request("GET", "/profile", headers={"Authorization": f"Bearer {expired_token}"})
        assert status == 401, f"Expected 401 for expired token, got {status}: {res}"
        assert "Token has expired" in str(res.get("detail", ""))
        print("[PASS] Expired token rejected with clear detail (401 Unauthorized).")

        # 2.6 Token with non-existent user account -> 401 Unauthorized
        ghost_token = jwt.encode(
            {"sub": "ghost_user_123456@example.com", "name": "Ghost", "role": "customer", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            jwt_secret,
            algorithm=jwt_algorithm
        )
        status, res = make_request("GET", "/profile", headers={"Authorization": f"Bearer {ghost_token}"})
        assert status == 401, f"Expected 401 for nonexistent user token, got {status}: {res}"
        print("[PASS] Token for deleted/nonexistent user rejected (401 Unauthorized).")

        # -------------------------------------------------------------
        # SUITE 3: Profile Endpoint Authorization
        # -------------------------------------------------------------
        print("\n--- Suite 3: Profile Endpoint Authorization ---")

        # 3.1 GET /profile with valid token -> 200 OK
        status, res = make_request("GET", "/profile", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and res.get("email") == customer_a_email, f"GET profile failed: {res}"
        assert res.get("role") == "customer"
        print("[PASS] Valid GET /profile returns authenticated profile details.")

        # 3.2 GET /profile with matching query param email -> 200 OK
        status, res = make_request("GET", f"/profile?email={customer_a_email}", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and res.get("email") == customer_a_email
        print("[PASS] GET /profile matching query email succeeded.")

        # 3.3 GET /profile with mismatched email query param -> 403 Forbidden
        status, res = make_request("GET", f"/profile?email={customer_b_email}", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 403, f"Expected 403 for cross-user profile access, got {status}: {res}"
        print("[PASS] Cross-user profile access blocked (403 Forbidden).")

        # 3.4 PUT /profile updating name for own account -> 200 OK
        status, res = make_request("PUT", "/profile", data={"name": "Customer A Verified"}, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and res.get("name") == "Customer A Verified"
        print("[PASS] Valid PUT /profile update succeeded.")

        # 3.5 PUT /profile with mismatched email -> 403 Forbidden
        status, res = make_request("PUT", "/profile", data={"email": customer_b_email, "name": "Hacked B"}, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 403, f"Expected 403 for cross-user profile update, got {status}: {res}"
        print("[PASS] Cross-user profile update blocked (403 Forbidden).")

        # -------------------------------------------------------------
        # SUITE 4: Booking Creation Spoofing & IDOR Protection
        # -------------------------------------------------------------
        print("\n--- Suite 4: Booking Creation Spoofing & IDOR Protection ---")

        # 4.1 Anonymous booking under existing registered user email -> 401 Unauthorized
        status, res = make_request("POST", "/bookings", data={
            "user_email": customer_a_email,
            "service": "Electrician",
            "provider": "Amit Electrical Services",
            "date": "2026-11-20",
            "description": "Anonymous spoof attempt under registered account"
        })
        assert status == 401, f"Expected 401 for anonymous booking under registered email, got {status}: {res}"
        assert "belongs to a registered FixNear account" in str(res.get("detail", ""))
        print("[PASS] Anonymous booking under registered user email blocked (401 Unauthorized).")

        # 4.2 Guest booking with unregistered email succeeds -> 200 OK
        guest_email = "guest_unregistered_client@example.com"
        status, guest_res = make_request("POST", "/bookings", data={
            "user_email": guest_email,
            "service": "Electrician",
            "provider": "Amit Electrical Services",
            "date": "2026-11-20",
            "description": "Guest client booking"
        })
        assert status == 200 and "booking_id" in guest_res
        created_booking_ids.append(guest_res["booking_id"])
        print("[PASS] Legitimate guest booking with unregistered email permitted (200 OK).")

        # 4.3 Create booking for Customer A with Bearer token
        status, b_res = make_request("POST", "/bookings", data={
            "service": "Electrician",
            "provider": "Amit Electrical Services",
            "date": "2026-11-20",
            "description": "Wiring repair for room"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and "booking_id" in b_res, f"Booking creation failed: {b_res}"
        booking_a_id = b_res["booking_id"]
        created_booking_ids.append(booking_a_id)
        print(f"[PASS] Customer A authenticated booking created (ID: {booking_a_id}).")

        # 4.4 Customer A lists bookings -> sees booking_a_id
        status, b_list = make_request("GET", "/bookings", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and isinstance(b_list, list)
        matching_a = [b for b in b_list if b["id"] == booking_a_id]
        assert len(matching_a) == 1, "Customer A did not see own booking"
        print("[PASS] Customer A lists own bookings successfully.")

        # 4.5 Customer A cannot query Customer B's bookings via user_email -> 403 Forbidden
        status, res = make_request("GET", f"/bookings?user_email={customer_b_email}", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 403, f"Expected 403 for cross-customer booking query, got {status}: {res}"
        print("[PASS] Customer querying another customer's bookings blocked (403 Forbidden).")

        # 4.6 Customer B lists bookings -> CANNOT see Customer A's booking
        status, b_list_b = make_request("GET", "/bookings", headers={"Authorization": f"Bearer {token_b}"})
        assert status == 200 and isinstance(b_list_b, list)
        matching_b = [b for b in b_list_b if b["id"] == booking_a_id]
        assert len(matching_b) == 0, "Customer B saw Customer A's booking in listing!"
        print("[PASS] Customer B listing excludes Customer A's booking.")

        # 4.7 Single-Booking IDOR Protection: GET /bookings/{id}
        # Customer B tries to directly fetch Customer A's booking by ID -> 403 Forbidden
        status, res = make_request("GET", f"/bookings/{booking_a_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert status == 403, f"Expected 403 IDOR block for Customer B, got {status}: {res}"
        print("[PASS] GET /bookings/{id} single-booking IDOR bypass blocked for unauthorized user (403 Forbidden).")

        # Customer A fetches own booking by ID -> 200 OK
        status, res = make_request("GET", f"/bookings/{booking_a_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and res.get("id") == booking_a_id
        print("[PASS] GET /bookings/{id} succeeds for legitimate booking owner (200 OK).")

        # Assigned provider (Amit) fetches booking by ID -> 200 OK
        status, res = make_request("GET", f"/bookings/{booking_a_id}", headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200 and res.get("id") == booking_a_id
        print("[PASS] GET /bookings/{id} succeeds for assigned provider Amit (200 OK).")

        # Unassigned provider (Saha) tries to fetch Amit's booking by ID -> 403 Forbidden
        status, res = make_request("GET", f"/bookings/{booking_a_id}", headers={"Authorization": f"Bearer {token_saha}"})
        assert status == 403, f"Expected 403 for unassigned provider Saha, got {status}: {res}"
        print("[PASS] GET /bookings/{id} blocked for unassigned provider Saha (403 Forbidden).")

        # -------------------------------------------------------------
        # SUITE 5: Provider Role Boundaries & Status Authorization
        # -------------------------------------------------------------
        print("\n--- Suite 5: Provider Role Boundaries & Status Authorization ---")

        # 5.1 Provider Amit lists bookings -> sees booking_a_id
        status, amit_bookings = make_request("GET", "/bookings", headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200 and any(b["id"] == booking_a_id for b in amit_bookings)
        print("[PASS] Assigned provider Amit sees incoming booking.")

        # 5.2 Provider Amit trying to filter by Saha Plumbing -> 403 Forbidden
        status, res = make_request("GET", "/bookings?provider=Saha%20Plumbing%20Services", headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 403, f"Expected 403 for provider cross-business query, got {status}: {res}"
        print("[PASS] Provider blocked from viewing other providers' bookings (403 Forbidden).")

        # 5.3 Customer A cannot Accept or Complete own booking -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": "Accepted"}, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 403, f"Expected 403 for customer accept, got {status}: {res}"
        status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": "Completed"}, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 403, f"Expected 403 for customer complete, got {status}: {res}"
        print("[PASS] Customer blocked from accepting or completing bookings (403 Forbidden).")

        # 5.4 Unassigned provider (Saha) cannot update Amit's booking -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": "Accepted"}, headers={"Authorization": f"Bearer {token_saha}"})
        assert status == 403, f"Expected 403 for unassigned provider update, got {status}: {res}"
        print("[PASS] Unassigned provider Saha blocked from updating Amit's booking (403 Forbidden).")

        # 5.5 Assigned provider (Amit) accepts booking -> 200 OK
        status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": "Accepted"}, headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200 and res.get("status") == "Accepted"
        print("[PASS] Assigned provider Amit successfully accepted booking (200 OK).")

        # 5.6 Assigned provider (Amit) completes booking -> 200 OK
        status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": "Completed"}, headers={"Authorization": f"Bearer {token_amit}"})
        assert status == 200 and res.get("status") == "Completed"
        print("[PASS] Assigned provider Amit successfully completed booking (200 OK).")

        # 5.7 Completed booking lock rule: cannot revert back to Pending/Accepted/Rejected -> 400 Bad Request
        for bad_status in ["Pending", "Accepted", "Rejected"]:
            status, res = make_request("PATCH", f"/bookings/{booking_a_id}/status", data={"status": bad_status}, headers={"Authorization": f"Bearer {token_amit}"})
            assert status == 400, f"Expected 400 lock violation for {bad_status}, got {status}: {res}"
        print("[PASS] Completed booking final lock verified: Reversion blocked (400 Bad Request).")

        # 5.8 Customer cancellation of own Pending booking
        status, b2_res = make_request("POST", "/bookings", data={
            "service": "Electrician",
            "provider": "Amit Electrical Services",
            "date": "2026-11-21",
            "description": "Ceiling light repair"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200
        booking2_id = b2_res["booking_id"]
        created_booking_ids.append(booking2_id)

        # Customer B cannot cancel Customer A's booking -> 403 Forbidden
        status, res = make_request("PATCH", f"/bookings/{booking2_id}/status", data={"status": "Rejected"}, headers={"Authorization": f"Bearer {token_b}"})
        assert status == 403, f"Expected 403 for cross-customer cancellation, got {status}: {res}"
        print("[PASS] Cross-customer cancellation blocked (403 Forbidden).")

        # Customer A cancels own Pending booking -> 200 OK
        status, res = make_request("PATCH", f"/bookings/{booking2_id}/status", data={"status": "Rejected"}, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and res.get("status") == "Rejected"
        print("[PASS] Legitimate customer cancellation of own booking verified (200 OK).")

        # -------------------------------------------------------------
        # SUITE 6: Review Creation Authorization & Spoofing Protection
        # -------------------------------------------------------------
        print("\n--- Suite 6: Review Authorization & Spoofing Protection ---")

        # 6.1 Non-owner (Customer B) attempting to review Customer A's completed booking -> 403 Forbidden
        status, res = make_request("POST", "/reviews", data={
            "booking_id": booking_a_id,
            "rating": 5,
            "comment": "Customer B review spoof attempt"
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert status == 403, f"Expected 403 for non-owner review spoof, got {status}: {res}"
        print("[PASS] Review identity spoofing blocked for non-owner (403 Forbidden).")

        # 6.2 Customer A attempting to review cancelled (Rejected) booking -> 400 Bad Request
        status, res = make_request("POST", "/reviews", data={
            "booking_id": booking2_id,
            "rating": 5,
            "comment": "Reviewing rejected booking"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for reviewing non-completed booking, got {status}: {res}"
        assert "Only completed bookings" in str(res.get("detail", ""))
        print("[PASS] Reviewing non-completed booking rejected (400 Bad Request).")

        # 6.3 Legitimate booking owner Customer A reviews Completed booking -> 200 OK
        status, res = make_request("POST", "/reviews", data={
            "booking_id": booking_a_id,
            "rating": 5,
            "comment": "Excellent and punctual service by Amit!"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 200 and "id" in res, f"Legitimate review failed: {res}"
        created_review_ids.append(res["id"])
        print("[PASS] Legitimate customer review submitted successfully (200 OK).")

        # 6.4 Duplicate review on same booking -> 400 Bad Request
        status, res = make_request("POST", "/reviews", data={
            "booking_id": booking_a_id,
            "rating": 4,
            "comment": "Second review attempt"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert status == 400, f"Expected 400 for duplicate review, got {status}: {res}"
        assert "already been submitted" in str(res.get("detail", ""))
        print("[PASS] Duplicate review submission rejected (400 Bad Request).")

        # 6.5 Public reviews list contains verified review
        status, reviews_list = make_request("GET", f"/reviews?booking_id={booking_a_id}")
        assert status == 200 and len(reviews_list) == 1
        assert reviews_list[0]["customer_email"] == customer_a_email
        print("[PASS] Public review list accurately reflects verified review.")

        # --- Suite 7: CORS Headers & Rate Limiting Enforcement ---
        print("\n--- Suite 7: CORS Headers & Rate Limiting Enforcement ---")

        # 7.1 CORS Headers on live server (port 8000)
        # Allowed origin receives Access-Control-Allow-Origin
        req = urllib.request.Request(f"{BASE_URL}/services", headers={"Origin": "http://localhost:5173"})
        with urllib.request.urlopen(req) as resp:
            assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
            assert resp.headers.get("Access-Control-Allow-Credentials") == "true"
        print("[PASS] Allowed origin receives Access-Control-Allow-Origin and credentials headers.")

        # Disallowed origin does NOT receive Access-Control-Allow-Origin
        req = urllib.request.Request(f"{BASE_URL}/services", headers={"Origin": "https://unauthorized-evil-site.com"})
        with urllib.request.urlopen(req) as resp:
            assert resp.headers.get("Access-Control-Allow-Origin") is None
        print("[PASS] Disallowed origin blocked from Access-Control-Allow-Origin.")

        # 7.2 Rate limiting enforcement on /login and /register
        # Spawn a controlled temporary test server with strict limits (3/minute) on dedicated port 8019
        rl_port = 8019
        rl_base = f"http://127.0.0.1:{rl_port}"
        rl_env = os.environ.copy()
        rl_env["LOGIN_RATE_LIMIT"] = "3/minute"
        rl_env["REGISTER_RATE_LIMIT"] = "3/minute"

        rl_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", str(rl_port)],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=rl_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        try:
            for _ in range(30):
                time.sleep(0.3)
                if is_port_open(rl_port):
                    break
            else:
                raise RuntimeError("Failed to start rate-limit test process.")

            def call_rl(ep, data):
                req_obj = urllib.request.Request(
                    f"{rl_base}{ep}",
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                try:
                    with urllib.request.urlopen(req_obj) as r:
                        return r.status, json.loads(r.read().decode("utf-8"))
                except urllib.error.HTTPError as e:
                    return e.code, json.loads(e.read().decode("utf-8"))

            # Test /login rate limit: 3 requests allowed, 4th throttled with 429
            for i in range(3):
                st, body = call_rl("/login", {"email": "nobody@example.com", "password": "wrong"})
                assert st == 401, f"Expected 401 on attempt {i+1}, got {st}: {body}"
            st4, body4 = call_rl("/login", {"email": "nobody@example.com", "password": "wrong"})
            assert st4 == 429, f"Expected 429 on 4th login attempt, got {st4}: {body4}"
            assert "rate limit exceeded" in str(body4).lower()
            print("[PASS] /login rate limit enforced: 4th attempt returned HTTP 429 Too Many Requests.")

            # Test /register rate limit: 3 requests allowed, 4th throttled with 429
            for i in range(3):
                st, body = call_rl("/register", {"name": "X", "email": "bad", "password": "1"})
                assert st == 400, f"Expected 400 on invalid register attempt {i+1}, got {st}: {body}"
            reg_st4, reg_body4 = call_rl("/register", {"name": "X", "email": "bad", "password": "1"})
            assert reg_st4 == 429, f"Expected 429 on 4th register attempt, got {reg_st4}: {reg_body4}"
            assert "rate limit exceeded" in str(reg_body4).lower()
            print("[PASS] /register rate limit enforced: 4th attempt returned HTTP 429 Too Many Requests.")

        finally:
            rl_proc.terminate()
            rl_proc.wait()
            print("[PASS] Controlled rate-limit test process terminated cleanly.")

    finally:
        try:
            # Cleanup temporary test records directly via MongoDB
            print("\n--- Cleaning Up Phase 8A Test Records ---")
            from pymongo import MongoClient
            from bson import ObjectId
            c = MongoClient(os.getenv("MONGO_URI") or "mongodb://localhost:27017/")
            db = c["local_service_marketplace"]

            if created_booking_ids:
                db["bookings"].delete_many({"_id": {"$in": [ObjectId(bid) for bid in created_booking_ids]}})
                db["reviews"].delete_many({"booking_id": {"$in": created_booking_ids}})
                print(f"[PASS] Removed {len(created_booking_ids)} test bookings & associated reviews.")

            if created_review_ids:
                db["reviews"].delete_many({"_id": {"$in": [ObjectId(rid) for rid in created_review_ids]}})

            if test_user_emails:
                db["users"].delete_many({"email": {"$in": test_user_emails}})
                print(f"[PASS] Removed test user accounts: {test_user_emails}")

            # Verify DB integrity: assert collection counts match baseline state before test
            for col, exp in initial_counts.items():
                actual = db[col].count_documents({})
                assert actual == exp, f"DB count mismatch for {col}: expected {exp}, got {actual}"
                print(f"[PASS] Collection '{col}' intact ({actual} documents).")
        finally:
            # Shutdown test process if started by this script
            if server_process is not None:
                print("[INFO] Terminating controlled Uvicorn test process...")
                try:
                    server_process.terminate()
                    server_process.wait(timeout=5)
                except Exception:
                    server_process.kill()
                print("[PASS] Uvicorn test process terminated cleanly.")

    print("\n==================================================================")
    print("--- ALL PHASE 8A SECURE AUTH TESTS PASSED SUCCESSFULLY! ---")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
