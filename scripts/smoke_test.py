import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


BASE_URL = "http://127.0.0.1:8765"
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {}
    if INTERNAL_API_TOKEN:
        headers["X-Internal-Token"] = INTERNAL_API_TOKEN
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def check_model_setting() -> bool:
    status, body = request("GET", "/settings/model")
    print("GET /settings/model", status, body)
    if status != 200:
        return False

    initial = json.loads(body)
    current_model = initial.get("activeModel")
    allowed_models = initial.get("allowedModels", [])
    target_model = "gemini-2.5-flash-lite"
    if not current_model or target_model not in allowed_models:
        print("FAIL: /settings/model returned invalid model data")
        return False

    success = False
    restored = False
    try:
        status, body = request(
            "PATCH",
            "/settings/model",
            {"model": target_model},
        )
        print("PATCH /settings/model", status, body)
        if status == 200 and json.loads(body).get("activeModel") == target_model:
            status, body = request("GET", "/settings/model")
            print("GET /settings/model after PATCH", status, body)
            success = (
                status == 200
                and json.loads(body).get("activeModel") == target_model
            )
    finally:
        status, body = request(
            "PATCH",
            "/settings/model",
            {"model": current_model},
        )
        restored = status == 200 and json.loads(body).get("activeModel") == current_model
        print("PATCH /settings/model restore", status, body)
        if not restored:
            print("FAIL: could not restore the active Gemini model")
    return success and restored


def main() -> int:
    checks = [
        ("GET", "/health", None, 200),
        ("GET", "/app", None, 200),
        ("GET", "/stores", None, 200),
        ("GET", "/documents", None, 200),
        (
            "GET",
            "/documents?tenantId=marcus&storeKey=curso-devops&active=all",
            None,
            200,
        ),
        (
            "GET",
            "/documents?tenantId=marcus&storeKey=curso-devops&active=all&integrityStatus=missing_local_file",
            None,
            200,
        ),
        (
            "GET",
            "/stores/stats?tenantId=marcus&storeKey=curso-devops",
            None,
            200,
        ),
        ("GET", "/queries", None, 200),
        ("GET", "/notes?tenantId=marcus&storeKey=curso-devops", None, 200),
    ]

    for method, path, payload, expected in checks:
        status, body = request(method, path, payload)
        print(method, path, status, body[:200] if len(body) > 200 else body)
        if status != expected:
            print(f"FAIL: expected {expected}, got {status}")
            return 1
        if path == "/app" and "Chat Local Gemini" not in body:
            print("GET /app missing expected page title")
            return 1

    if not check_model_setting():
        print("FAIL: runtime Gemini model setting")
        return 1

    # Verifica que /stores/stats inclui bloco integrity
    status, body = request("GET", "/stores/stats?tenantId=marcus&storeKey=curso-devops")
    if status == 200:
        parsed = json.loads(body)
        if "integrity" not in parsed:
            print("FAIL: /stores/stats missing 'integrity' block")
            return 1
        print("GET /stores/stats integrity block: OK")

    # POST /stores/integrity-check
    status, body = request(
        "POST",
        "/stores/integrity-check",
        {"tenantId": "marcus", "storeKey": "curso-devops"},
    )
    print("POST /stores/integrity-check", status, body[:200] if len(body) > 200 else body)
    if status != 200:
        print(f"FAIL: expected 200, got {status}")
        return 1
    parsed = json.loads(body)
    if "summary" not in parsed or "items" not in parsed:
        print("FAIL: /stores/integrity-check missing 'summary' or 'items'")
        return 1
    print("POST /stores/integrity-check: OK")

    # POST /stores/rebuild-plan
    status, body = request(
        "POST",
        "/stores/rebuild-plan",
        {"tenantId": "marcus", "storeKey": "curso-devops"},
    )
    print("POST /stores/rebuild-plan", status, body[:200] if len(body) > 200 else body)
    if status != 200:
        print(f"FAIL: expected 200, got {status}")
        return 1
    parsed = json.loads(body)
    required_keys = {"canRebuildSafely", "reason", "activeAvailableDocuments",
                     "activeMissingDocuments", "inactiveDocuments"}
    missing = required_keys - set(parsed.keys())
    if missing:
        print(f"FAIL: /stores/rebuild-plan missing keys: {missing}")
        return 1
    print("POST /stores/rebuild-plan: OK")

    # POST /query com store inexistente
    status, body = request(
        "POST",
        "/query",
        {"tenantId": "ihx", "storeKey": "access-pro", "question": "ping"},
    )
    print("POST /query missing store", status, body)
    if status != 404:
        return 1

    print("Smoke test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
