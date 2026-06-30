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


def main() -> int:
    checks = [
        ("GET", "/health", None, 200),
        ("GET", "/app", None, 200),
        ("GET", "/stores", None, 200),
        ("GET", "/documents", None, 200),
        ("GET", "/queries", None, 200),
    ]

    for method, path, payload, expected in checks:
        status, body = request(method, path, payload)
        print(method, path, status, body)
        if status != expected:
            return 1
        if path == "/app" and "Chat Local Gemini" not in body:
            print("GET /app missing expected page title")
            return 1

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
