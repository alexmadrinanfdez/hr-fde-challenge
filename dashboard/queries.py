import json
import os
import urllib.request


def _get(path: str) -> list[dict]:
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("API_KEY", "")

    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    url = f"{base_url}{path}"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_calls() -> list[dict]:
    return _get("/calls")


def get_loads() -> list[dict]:
    return _get("/loads")