"""
regeocode_corrections.py
-------------------------
Finds Firestore 'corrections' documents where status == 'approved' and
lat/lng are still missing, geocodes the corrected city/state/country,
and writes the coordinates back into the document.

Run this any time after approving corrections in the Firebase console:
    python3 regeocode_corrections.py

Requires:
    pip install firebase-admin geopy

Setup (one-time):
    1. Firebase Console -> Project settings -> Service accounts
       -> Generate new private key -> save as serviceAccountKey.json
       in this same folder.
"""

import time
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# ── Config ────────────────────────────────────────────────────────────────────
# SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
# seconds between geocoding requests (Nominatim requires >= 1)
DELAY = 1.1
MAX_RETRIES = 3

# ── Init Firebase Admin ──────────────────────────────────────────────────────
# cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ── Init geocoder ─────────────────────────────────────────────────────────────
geolocator = Nominatim(user_agent="ftc_teams_map_corrections_v1", timeout=10)


def geocode_with_fallback(city, state, country):
    """Try full address first, then progressively simpler fallbacks."""
    attempts = [
        ", ".join(filter(None, [city, state, country])),
        ", ".join(filter(None, [city, country])),
        country,
    ]
    seen = set()
    attempts = [a for a in attempts if a and a not in seen and not seen.add(a)]

    for attempt in attempts:
        for retry in range(MAX_RETRIES):
            try:
                result = geolocator.geocode(attempt)
                if result:
                    return round(result.latitude, 6), round(result.longitude, 6)
                break
            except GeocoderTimedOut:
                print(
                    f"    Timeout on '{attempt}', retry {retry+1}/{MAX_RETRIES}")
                time.sleep(2)
            except GeocoderServiceError as e:
                print(f"    Service error: {e}")
                time.sleep(5)
                break
        time.sleep(DELAY)

    return None, None


def main():
    corrections_ref = db.collection("corrections")

    # approved corrections missing lat/lng
    query = corrections_ref.where(
        "status", "==", "approved").where("lat", "==", None)
    docs = list(query.stream())

    print(f"Found {len(docs)} approved correction(s) needing geocoding.\n")

    if not docs:
        print("Nothing to do.")
        return

    updated = 0
    failed = 0

    for doc in docs:
        data = doc.to_dict()
        team_number = data.get("teamNumber")
        city = data.get("city")
        state = data.get("state")
        country = data.get("country")

        label = f"Team #{team_number}: {', '.join(filter(None, [city, state, country])) or '(no location given)'}"
        print(label)

        if not (city or state or country):
            print("    ⚠ No location fields provided — skipping (note-only correction)")
            continue

        lat, lng = geocode_with_fallback(city, state, country)

        if lat is not None:
            doc.reference.update({"lat": lat, "lng": lng})
            print(f"    ✅ {lat}, {lng}")
            updated += 1
        else:
            print(f"    ⚠ Could not geocode")
            failed += 1

    print(f"\nDone. Updated: {updated}  Failed: {failed}")
    print("Reload your map — the corrected pins should now appear in the right place.")


if __name__ == "__main__":
    main()
