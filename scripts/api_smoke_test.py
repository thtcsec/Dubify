"""Smoke-test Dubify API (no secrets printed)."""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
YT = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def req(method: str, path: str, data: dict | None = None, multipart: bool = False):
    url = f"{API}{path}" if path.startswith("/") else f"{API}/{path}"
    if method == "GET":
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    body = None
    headers = {}
    if multipart and data:
        import uuid

        boundary = uuid.uuid4().hex
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        parts = []
        for k, v in data.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as r:
        return r.status, json.loads(r.read().decode())


def main():
    results = []

    try:
        with urllib.request.urlopen(f"{BASE}/health", timeout=30) as r:
            health = json.loads(r.read().decode())
        results.append(("health", r.status, health.get("status")))
    except Exception as e:
        print("FAIL health:", e)
        sys.exit(1)

    try:
        code, settings = req("GET", "/settings")
        results.append(("settings_get", code, {
            "engine": settings.get("processing_engine"),
            "mode": settings.get("processing_mode"),
            "cloud_ready": (settings.get("cloud_status") or {}).get("ready"),
        }))
    except Exception as e:
        results.append(("settings_get", "ERR", str(e)[:120]))

    try:
        code, info = req("POST", "/fetch-info", {"url": YT}, multipart=True)
        results.append(("fetch_info_youtube", code, {
            "title": (info.get("title") or "")[:60],
            "source": info.get("source"),
            "duration": info.get("duration"),
        }))
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        results.append(("fetch_info_youtube", e.code, body))
    except Exception as e:
        results.append(("fetch_info_youtube", "ERR", str(e)[:120]))

    for preset, engine, mode in [
        ("hybrid", "local", "hybrid"),
        ("local_offline", "local", "offline"),
        ("cloud_online", "cloud", "online"),
    ]:
        try:
            code, saved = req("POST", "/settings", {
                "processing_engine": engine,
                "processing_mode": mode,
            })
            code2, got = req("GET", "/settings")
            ok = got.get("processing_engine") == engine and got.get("processing_mode") == mode
            results.append((f"preset_{preset}", code, {"saved_ok": ok}))
            # restore hybrid
            req("POST", "/settings", {"processing_engine": "local", "processing_mode": "hybrid"})
        except Exception as e:
            results.append((f"preset_{preset}", "ERR", str(e)[:80]))

    print(json.dumps(results, indent=2, ensure_ascii=False))
    failed = [r for r in results if r[1] not in (200, 201) and r[1] != "ERR" and r[1] != 200]
    if any(r[1] == "ERR" for r in results):
        sys.exit(2)
    print("OK")


if __name__ == "__main__":
    main()
