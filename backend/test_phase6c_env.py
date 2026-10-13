import os
import re
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

def test_git_hygiene_and_gitignore():
    print("--- Suite 1: Root .gitignore & Environment Files Hygiene ---")
    
    root_gitignore = ROOT_DIR / ".gitignore"
    assert root_gitignore.is_file(), "Root .gitignore file missing!"
    gitignore_text = root_gitignore.read_text(encoding="utf-8")

    required_patterns = [
        "backend/venv/",
        "__pycache__/",
        "*.py[cod]",
        "frontend/node_modules/",
        "frontend/dist/",
        ".env",
        ".env.*",
        "!.env.example",
        ".pytest_cache/",
        ".vscode/",
        ".idea/",
        ".DS_Store",
        "Thumbs.db",
    ]

    for pat in required_patterns:
        assert pat in gitignore_text, f"Missing required pattern in root .gitignore: {pat}"
        print(f"[PASS] Excluded pattern verified in root .gitignore: {pat}")

    # Check frontend .gitignore
    fe_gitignore = FRONTEND_DIR / ".gitignore"
    assert fe_gitignore.is_file(), "Frontend .gitignore file missing!"
    fe_git_text = fe_gitignore.read_text(encoding="utf-8")
    for fe_pat in [".env", ".env.*", "!.env.example"]:
        assert fe_pat in fe_git_text, f"Missing pattern in frontend .gitignore: {fe_pat}"
    print("[PASS] Frontend .gitignore env rules verified.")

    # Check example environment files
    example_files = [
        ROOT_DIR / ".env.example",
        BACKEND_DIR / ".env.example",
        FRONTEND_DIR / ".env.example",
    ]
    for ex_file in example_files:
        assert ex_file.is_file(), f"Example env file missing: {ex_file}"
        content = ex_file.read_text(encoding="utf-8")
        # Ensure no accidental secret leakage
        assert "password" not in content.lower() or "not" in content.lower(), f"Potential secret in {ex_file}"
        assert "secret" not in content.lower() or "not" in content.lower(), f"Potential secret in {ex_file}"
        print(f"[PASS] Safe example env file verified: {ex_file.name}")

def test_backend_env_configuration():
    print("\n--- Suite 2: Backend MONGO_URI Configuration & Dotenv Loading ---")
    
    main_py = BACKEND_DIR / "main.py"
    main_text = main_py.read_text(encoding="utf-8")
    
    assert "load_dotenv" in main_text, "main.py must use python-dotenv load_dotenv()"
    assert "MONGO_URI" in main_text, "main.py must reference MONGO_URI"
    assert "mongodb://localhost:27017/" in main_text, "main.py must provide localhost fallback"
    print("[PASS] backend/main.py uses load_dotenv() and MONGO_URI with localhost fallback.")

    # Test importing and fallback logic
    from dotenv import load_dotenv
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
    from pymongo import MongoClient
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    server_info = client.server_info()
    assert server_info is not None, "Failed to connect to MongoDB via MONGO_URI fallback!"
    print(f"[PASS] Successfully connected to MongoDB using MONGO_URI fallback ({mongo_uri}).")

def test_frontend_vite_api_url_configuration():
    print("\n--- Suite 3: Frontend VITE_API_URL Configuration ---")
    
    config_js = FRONTEND_DIR / "src" / "config.js"
    assert config_js.is_file(), "frontend/src/config.js missing!"
    config_text = config_js.read_text(encoding="utf-8")
    
    assert "VITE_API_URL" in config_text, "config.js must inspect VITE_API_URL"
    assert "http://127.0.0.1:8000" in config_text, "config.js must provide http://127.0.0.1:8000 fallback"
    assert "API_BASE_URL" in config_text, "config.js must export API_BASE_URL"
    print("[PASS] frontend/src/config.js exports API_BASE_URL with VITE_API_URL and fallback.")

    # Check that no hardcoded http://127.0.0.1:8000 remains in components or App.jsx
    components_dir = FRONTEND_DIR / "src" / "components"
    all_files = list(components_dir.glob("*.jsx")) + [FRONTEND_DIR / "src" / "App.jsx"]
    
    hardcoded_found = []
    for f in all_files:
        content = f.read_text(encoding="utf-8")
        # Match literal 'http://127.0.0.1:8000 or "http://127.0.0.1:8000
        if re.search(r"['\"]http://127\.0\.0\.1:8000", content):
            hardcoded_found.append(f.name)
    
    assert len(hardcoded_found) == 0, f"Found hardcoded API URLs in: {hardcoded_found}"
    print(f"[PASS] Verified 0 hardcoded backend URLs across {len(all_files)} frontend files.")

def test_api_integration():
    print("\n--- Suite 4: End-to-End API Integration with Configured Fallbacks ---")
    
    python_exe = sys.executable
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server readiness
        server_ready = False
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/db-test", timeout=1) as resp:
                    if resp.status == 200:
                        server_ready = True
                        break
            except Exception:
                time.sleep(0.3)
        assert server_ready, "Server failed to start within timeout"
        print("[PASS] Backend server spawned and responding on http://127.0.0.1:8000.")

        # Test GET /services
        with urllib.request.urlopen("http://127.0.0.1:8000/services") as resp:
            services = json.loads(resp.read().decode("utf-8"))
            assert len(services) == 6, f"Expected 6 services, got {len(services)}"
        print("[PASS] GET /services returned 6 services.")

        # Test GET /providers
        with urllib.request.urlopen("http://127.0.0.1:8000/providers") as resp:
            providers = json.loads(resp.read().decode("utf-8"))
            assert len(providers) == 3, f"Expected 3 providers, got {len(providers)}"
        print("[PASS] GET /providers returned 3 providers.")

        # Test GET /bookings with auth header
        req = urllib.request.Request(
            "http://127.0.0.1:8000/bookings?provider=Amit%20Electrical%20Services",
            headers={"X-Role": "provider"}
        )
        with urllib.request.urlopen(req) as resp:
            bookings = json.loads(resp.read().decode("utf-8"))
            assert isinstance(bookings, list)
        print("[PASS] GET /bookings returned valid list with X-Role header.")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[PASS] Uvicorn server terminated cleanly.")

def test_database_integrity():
    print("\n--- Suite 5: MongoDB Integrity Verification ---")
    from pymongo import MongoClient
    mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
    db = MongoClient(mongo_uri)["local_service_marketplace"]
    
    expected_counts = {
        "services": 6,
        "users": 4,
        "providers": 3,
        "reviews": 1,
        "bookings": 12
    }
    for col, count in expected_counts.items():
        actual = db[col].count_documents({})
        assert actual == count, f"Collection {col} count mismatch: expected {count}, got {actual}"
        print(f"[PASS] Collection '{col}' intact with {actual} documents.")

def run_all_tests():
    print("==================================================================")
    print("--- Phase 6C: Git Hygiene & Environment Configuration Tests ---")
    print("==================================================================")
    test_git_hygiene_and_gitignore()
    test_backend_env_configuration()
    test_frontend_vite_api_url_configuration()
    test_api_integration()
    test_database_integrity()
    print("\n==================================================================")
    print("--- ALL PHASE 6C TESTS PASSED SUCCESSFULLY! ---")
    print("==================================================================")

if __name__ == "__main__":
    run_all_tests()
