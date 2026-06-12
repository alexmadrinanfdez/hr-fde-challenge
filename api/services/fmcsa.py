import json
import os
import urllib.request
import urllib.error
import urllib.parse


FMCSA_BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services/carriers"
FMCSA_TIMEOUT_SECONDS = 10


class FMCSAError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def verify_carrier(mc_number: str) -> dict:
    web_key = os.environ.get("FMCSA_WEB_KEY", "")

    if not web_key:
        raise FMCSAError("fmcsa_not_configured")

    params = urllib.parse.urlencode({"webKey": web_key})
    url = f"{FMCSA_BASE_URL}/docket-number/{mc_number}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=FMCSA_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read()).get("content", {})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "mc_number": mc_number,
                "legal_name": None,
                "dot_number": None,
                "authorized": False,
                "reason": "not_found",
            }
        raise FMCSAError("fmcsa_unexpected_response")
    except urllib.error.URLError:
        raise FMCSAError("fmcsa_unreachable")
    except TimeoutError:
        raise FMCSAError("fmcsa_timeout")

    if not data:
        return {
            "mc_number": mc_number,
            "legal_name": None,
            "dot_number": None,
            "authorized": False,
            "reason": "not_found",
        }

    carrier = data.pop().get("carrier", {})

    return {
        "mc_number": mc_number,
        "legal_name": carrier.get("legalName"),
        "dot_number": str(carrier.get("dotNumber")),
        "authorized": carrier.get("allowedToOperate") == "Y",
        "reason": None if carrier.get("allowedToOperate") == "Y" else "not_authorized",
    }