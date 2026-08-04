"""
fetch_teams.py
--------------
Fetches all FTC teams from the official FIRST FTC API and geocodes
their city/state/country to lat/lng using OpenStreetMap Nominatim.
Outputs ftc_teams.json for use with ftc_map.html.

Setup:
    pip install requests

Usage:
    1. Register for a FIRST API token at:
       https://ftc-events.firstinspires.org/services/API
    2. Fill in YOUR_USERNAME and YOUR_TOKEN below.
    3. Run: python fetch_teams.py
    4. Open ftc_map.html in a browser (you may need a local server,
       e.g. `python -m http.server 8000` then visit localhost:8000)
"""

import requests
import json
import time
from requests.auth import HTTPBasicAuth
import base64


# ── Config ────────────────────────────────────────────────────────────────────
USERNAME = "weliwq"   # FIRST API username
TOKEN = "1EEEE6E6-C13A-46BE-B060-5DE2DB7BFCE1"      # FIRST API token
AUTH_KEY = "1EEEE6E6-C13A-46BE-B060-5DE2DB7BFCE1"
# SEASON = 2024              # Change to 2025 for the 2025–26 season
# OUTPUT = "ftc_teams.json"
# ─────────────────────────────────────────────────────────────────────────────

# BASE_URL = "https://ftc-api.firstinspires.org/v2.0"

SEASON = 2025
OUTPUT = "ftc_teams_raw.json"

_token = base64.b64encode(f"{USERNAME}:{AUTH_KEY}".encode()).decode()
HEADERS = {"Authorization": f"Basic {_token}"}
BASE_URL = "https://ftc-api.firstinspires.org/v2.0"

# tag/Season-Data/paths/~1v2.0~1{season}~1teams/get
def main():
    all_teams, page = [], 1
    print(f"Fetching FTC {SEASON} teams...")

    while True:
        resp = requests.get(
            f"{BASE_URL}/{SEASON}/teams",
            params={"page": page},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 401:
            raise SystemExit(
                "❌  401 Unauthorized — check USERNAME and AUTH_KEY")
        resp.raise_for_status()

        data = resp.json()
        batch = data.get("teams", [])
        total_pages = data.get("pageTotal", 1)
        all_teams.extend(batch)

        print(f"  Page {page}/{total_pages} — {len(all_teams)} teams so far")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.15)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_teams, f, indent=2, ensure_ascii=False)

    print(f"\n✅  Saved {len(all_teams)} teams → {OUTPUT}")


if __name__ == "__main__":
    main()

# def get_all_teams() -> list[dict]:
#     """Paginate through all FTC teams for a given season."""
#     all_teams = []
#     page = 1

#     print(f"Fetching FTC {SEASON} teams...")
#     while True:
#         resp = requests.get(
#             f"{BASE_URL}/{SEASON}/teams",
#             params={"page": page},
#             auth=HTTPBasicAuth(USERNAME, TOKEN),
#             timeout=10,
#         )
#         resp.raise_for_status()
#         data = resp.json()

#         batch = data.get("teams", [])
#         all_teams.extend(batch)
#         total_pages = data.get("pageTotal", 1)

#         print(f"  Page {page}/{total_pages} — {len(all_teams)} teams fetched")

#         if page >= total_pages:
#             break
#         page += 1
#         time.sleep(0.1)  # be polite to the FIRST API

#     print(f"Total teams fetched: {len(all_teams)}\n")
#     return all_teams


# def geocode_unique_locations(teams: list[dict]) -> dict[tuple, dict | None]:
#     """
#     Geocode each unique (city, state, country) combination once,
#     then reuse the result for all teams at the same location.
#     Nominatim allows 1 request/sec; we sleep 1.1s to be safe.
#     """
#     unique: dict[tuple, dict | None] = {}
#     for t in teams:
#         key = (t.get("city", ""), t.get("stateProv", ""), t.get("country", ""))
#         if key not in unique:
#             unique[key] = None

#     total = len(unique)
#     print(f"Geocoding {total} unique locations (this takes ~{total}s)...")

#     for i, (city, state, country) in enumerate(unique):
#         # Build query from non-empty parts
#         query = ", ".join(p for p in [city, state, country] if p)
#         if not query:
#             continue

#         try:
#             resp = requests.get(
#                 "https://nominatim.openstreetmap.org/search",
#                 params={"q": query, "format": "json", "limit": 1},
#                 headers={"User-Agent": "FTCTeamMap/1.0 (educational project)"},
#                 timeout=5,
#             )
#             results = resp.json()
#             if results:
#                 unique[(city, state, country)] = {
#                     "lat": float(results[0]["lat"]),
#                     "lng": float(results[0]["lon"]),
#                 }
#         except Exception as e:
#             print(f"  WARNING: Could not geocode '{query}': {e}")

#         if (i + 1) % 50 == 0:
#             print(f"  {i + 1}/{total} locations geocoded...")

#         time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

#     geocoded = sum(1 for v in unique.values() if v)
#     print(f"Geocoded: {geocoded}/{total} locations succeeded\n")
#     return unique


# def build_output(teams: list[dict], geo: dict[tuple, dict | None]) -> list[dict]:
#     """Merge team data with geocoded coordinates."""
#     output = []
#     skipped = 0

#     for t in teams:
#         key = (t.get("city", ""), t.get("stateProv", ""), t.get("country", ""))
#         coords = geo.get(key)
#         if not coords:
#             skipped += 1
#             continue

#         # Use nameShort if available, otherwise fall back to nameFull
#         name = (t.get("nameShort") or t.get("nameFull") or "Unknown").strip()

#         output.append({
#             "number":  t.get("teamNumber"),
#             "name":    name,
#             "city":    t.get("city", ""),
#             "state":   t.get("stateProv", ""),
#             "country": t.get("country", ""),
#             "school":  t.get("schoolName", ""),
#             "lat":     coords["lat"],
#             "lng":     coords["lng"],
#         })

#     if skipped:
#         print(f"Skipped {skipped} teams (geocoding failed for their location)")

#     return output


# def main():
#     teams = get_all_teams()
#     geo = geocode_unique_locations(teams)
#     output = build_output(teams, geo)

#     with open(OUTPUT, "w", encoding="utf-8") as f:
#         json.dump(output, f, indent=2, ensure_ascii=False)

#     print(f"✓ Saved {len(output)} teams to {OUTPUT}")
#     print("  Open ftc_map.html (with a local server) to view the map.")


# if __name__ == "__main__":
#     main()
