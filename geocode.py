"""
geocode.py
----------
Step 1: Geocodes unique_locations.json (with caching + rate limiting)
Step 2: Merges lat/lng back into teams_to_geocode.json
Step 3: Outputs ftc_teams.json ready for the map

Run: python3 geocode.py
(expects unique_locations.json and teams_to_geocode.json in same folder)

Safe to interrupt and re-run — already-geocoded locations are cached.
"""

import json
import time
import sys
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# ── Config ────────────────────────────────────────────────────────────────────
LOCATIONS_FILE = Path('unique_locations.json')
TEAMS_FILE = Path('teams_to_geocode.json')
OUTPUT_FILE = Path('ftc_teams.json')
CACHE_FILE = Path('geocode_cache.json')   # saves progress between runs

DELAY = 1.1   # seconds between requests (Nominatim requires >= 1)
TIMEOUT = 10    # seconds per request
MAX_RETRIES = 3

# ── Geocoder setup ────────────────────────────────────────────────────────────
geolocator = Nominatim(user_agent="ftc_teams_map_v1", timeout=TIMEOUT)


def geocode_with_fallback(geocode_str: str, city: str, country: str) -> tuple:
    """
    Try geocoding with progressively simpler strings:
    1. Full string (city, state, country)
    2. City + country only
    3. Country only (last resort so something shows up)
    Returns (lat, lng) or (None, None)
    """
    attempts = [
        geocode_str,
        ', '.join(filter(None, [city, country])),
        country if country else None,
    ]
    # deduplicate while preserving order
    seen = set()
    attempts = [a for a in attempts if a and a not in seen and not seen.add(a)]

    for attempt in attempts:
        for retry in range(MAX_RETRIES):
            try:
                result = geolocator.geocode(attempt)
                if result:
                    return round(result.latitude, 6), round(result.longitude, 6)
                break  # no result, try next attempt string
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

# ── Load cache ────────────────────────────────────────────────────────────────


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(
        cache, indent=2, ensure_ascii=False), encoding='utf-8')

# ── Step 1: Geocode unique locations ─────────────────────────────────────────


def geocode_locations():
    locations = json.loads(LOCATIONS_FILE.read_text(encoding='utf-8'))
    cache = load_cache()

    total = len(locations)
    done = sum(1 for l in locations if l['geocode_str'] in cache)
    remaining = total - done

    print(f"Unique locations: {total}")
    print(f"Already cached:   {done}")
    print(f"To geocode:       {remaining}")
    if remaining == 0:
        print("All locations already cached — skipping geocoding step.")
    else:
        print(f"Estimated time:   ~{remaining * DELAY / 60:.1f} minutes\n")

    for i, loc in enumerate(locations):
        key = loc['geocode_str']
        if key in cache:
            loc['lat'] = cache[key]['lat']
            loc['lng'] = cache[key]['lng']
            continue

        print(f"[{i+1}/{total}] {key}")
        lat, lng = geocode_with_fallback(
            loc['geocode_str'], loc['city'], loc['country']
        )
        loc['lat'] = lat
        loc['lng'] = lng

        cache[key] = {'lat': lat, 'lng': lng}
        save_cache(cache)  # save after every result so progress isn't lost

        if lat is None:
            print(f"    ⚠ Could not geocode: {key}")

        time.sleep(DELAY)

    # save updated locations file
    LOCATIONS_FILE.write_text(
        json.dumps(locations, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"\nGeocoding complete. Cache saved to {CACHE_FILE}")
    return {loc['geocode_str']: (loc['lat'], loc['lng']) for loc in locations}

# ── Step 2: Merge lat/lng into teams ─────────────────────────────────────────


def merge_into_teams(coord_map: dict):
    teams = json.loads(TEAMS_FILE.read_text(encoding='utf-8'))

    matched = 0
    unmatched = 0

    for team in teams:
        key = team.get('geocode_str', '')
        coords = coord_map.get(key)
        if coords and coords[0] is not None:
            team['lat'] = coords[0]
            team['lng'] = coords[1]
            matched += 1
        else:
            team['lat'] = None
            team['lng'] = None
            unmatched += 1

    OUTPUT_FILE.write_text(
        json.dumps(teams, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"\nTeams with coordinates:    {matched:,}")
    print(f"Teams without coordinates: {unmatched:,}")
    print(f"Output written to {OUTPUT_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not LOCATIONS_FILE.exists():
        print(
            f"ERROR: {LOCATIONS_FILE} not found. Run extract_teams.py first.")
        sys.exit(1)
    if not TEAMS_FILE.exists():
        print(f"ERROR: {TEAMS_FILE} not found. Run extract_teams.py first.")
        sys.exit(1)

    print("=== Step 1: Geocoding unique locations ===")
    coord_map = geocode_locations()

    print("\n=== Step 2: Merging coordinates into teams ===")
    merge_into_teams(coord_map)

    print("\nDone! ftc_teams.json is ready for the map.")
