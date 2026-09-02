"""
Vahan Database Lookup for VehicleTrack

Real Vahan API requires Government approval.
This module is structured to drop in the real API when approved.

For now: returns mock data for known plates, None for unknown.

Real API docs: https://vahan.parivahan.gov.in/vahanservice/
"""

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── CONFIG ────────────────────────────────────────────────
VAHAN_API_KEY = os.environ.get("VAHAN_API_KEY", "")
VAHAN_API_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/api/rc-details"

# ── MOCK DATA ─────────────────────────────────────────────
# For demo purposes — owner details loaded from env vars so no
# personal info is ever committed to GitHub.
# Set DEMO_NAME, DEMO_PHONE, DEMO_EMAIL in your .env file.
DEMO_NAME  = os.environ.get("DEMO_NAME",  "Demo Owner")
DEMO_PHONE = os.environ.get("DEMO_PHONE", "+910000000000")
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@example.com")

MOCK_DB = {
    "KA0112234":  {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Bengaluru"},
    "KA015678":   {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Bengaluru"},
    "TN05AT7024": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Chennai"},
    "MH04CD1234": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Mumbai"},
    "DL09W6392":  {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Delhi"},
    "KA0112236":  {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Bengaluru"},
    "KL11AB1234": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Kerala"},
    "KL09CA1671": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Kerala"},
    "KL07CD5678": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Kerala"},
    "KL15EF9012": {"name": DEMO_NAME, "phone": DEMO_PHONE, "email": DEMO_EMAIL, "city": "Kerala"},
}


def lookup_owner(plate):
    """
    Look up vehicle owner details by plate number.
    Returns dict with keys: name, phone, email, city
    Returns None if not found.
    """
    if not plate or plate == "UNKNOWN":
        return None

    plate = plate.upper().replace(" ", "").replace("-", "")

    # Try real Vahan API first (if key available)
    if VAHAN_API_KEY:
        try:
            response = requests.post(
                VAHAN_API_URL,
                json={"regNo": plate},
                headers={"x-api-key": VAHAN_API_KEY},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "name":  data.get("ownerName", "Unknown"),
                    "phone": data.get("mobileNo", ""),
                    "email": "",
                    "city":  data.get("regDistrict", ""),
                }
        except Exception as e:
            print(f"  [Vahan] API error: {e}, falling back to mock")

    # Fall back to mock DB
    return MOCK_DB.get(plate, None)