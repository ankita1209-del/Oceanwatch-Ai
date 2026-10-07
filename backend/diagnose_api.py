"""Check the local OceanWatch API without dumping full observations.

Run while the API is running:
    python -m backend.diagnose_api
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("OCEANWATCH_API_URL", "http://localhost:8000").rstrip("/")
ENDPOINTS = (
    ("GET", "/", None),
    ("GET", "/api/health", None),
    ("GET", "/docs", None),
    ("GET", "/api/events?limit=5", "events"),
    ("GET", "/api/history?lat=0&lon=0&limit=5", "history"),
    ("GET", "/api/risk-map?limit=5", "geojson"),
    ("GET", "/api/alerts?limit=5", "alerts"),
)


def summarize(body: bytes, kind: str | None) -> str:
    if kind is None:
        return "reachable"
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return f"non-JSON response ({len(body)} bytes)"
    if kind in {"events", "alerts"}:
        return f"{len(data)} records" if isinstance(data, list) else "unexpected response shape"
    if kind == "history":
        points = data.get("history", []) if isinstance(data, dict) else []
        return f"{len(points)} daily buckets"
    features = data.get("features", []) if isinstance(data, dict) else []
    return f"GeoJSON FeatureCollection, {len(features)} features"


def main() -> int:
    failures = 0
    print(f"API base URL: {BASE_URL}")
    for method, path, kind in ENDPOINTS:
        request = Request(f"{BASE_URL}{path}", method=method)
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read()
                status = response.status
                success = 200 <= status < 300
                summary = summarize(body, kind)
        except HTTPError as exc:
            status = exc.code
            success = False
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                summary = payload.get("detail", payload.get("error", "HTTP error"))
                if isinstance(summary, (dict, list)):
                    summary = json.dumps(summary, ensure_ascii=True)
            except Exception:
                summary = "HTTP error"
        except (URLError, TimeoutError, OSError) as exc:
            status = "CONNECTION FAILED"
            success = False
            summary = str(exc.reason if isinstance(exc, URLError) else exc)
        print(f"{method} {path}: {status} {'OK' if success else 'FAILED'} - {summary}")
        failures += not success
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
