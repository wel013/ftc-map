"""
extract_teams.py
----------------
Run: python3 extract_teams.py ftc_teams_raw.json

Outputs:
  teams_to_geocode.json   – clean list of teams with fields needed for geocoding
  unique_locations.json   – deduplicated city+state+country combos (to geocode once each)
"""

import json
import sys
import collections
from pathlib import Path

COUNTRY_NORMALIZE = {
    'USA':                  'United States',
    # pycountry says "Korea, Republic of"
    'South Korea':          'South Korea',
    'Türkiye':              'Turkey',
    'Vietnam':              'Vietnam',               # pycountry says "Viet Nam"
    'Moldova':              'Moldova',
    'Venezuela':            'Venezuela',
    'Czech Republic':       'Czechia',
    'Macedonia':            'North Macedonia',
    'Laos':                 'Laos',
    'Chinese Taipei':       'Taiwan',                # for geocoding purposes
    'Bosnia-Herzegovina':   'Bosnia and Herzegovina',
    'Ivory Coast':          "Côte d'Ivoire",
    # geocode by city+state only, skip country
    'Independent':          None,
}


def main(path: str):
    data = json.loads(Path(path).read_text(encoding='utf-8'))

    # unwrap if object
    if isinstance(data, dict):
        data = next(iter(data.values()))

    print(f"Loaded {len(data):,} teams")

    teams = []
    location_counter = collections.Counter()

    for t in data:
        city = (t.get('city') or '').strip()
        state = (t.get('stateProv') or '').strip()
        country = (t.get('country') or '').strip()

        normalized_country = COUNTRY_NORMALIZE.get(country, country)
        geocode_parts = [city, state]
        if normalized_country:
            geocode_parts.append(normalized_country)

        entry = {
            'number':    t.get('teamNumber'),
            'nameFull':  (t.get('nameFull') or '').strip(),
            'nameShort': (t.get('nameShort') or '').strip(),
            'school':    (t.get('schoolName') or None),
            'city':      city,
            'state':     state,
            'country':   country,
            'geocode_str': ', '.join(filter(None, geocode_parts)),
        }
        teams.append(entry)

        # track unique locations for deduplication
        loc_key = (city, state, country)
        location_counter[loc_key] += 1

    # unique locations sorted by team count (most common first)
    unique_locations = [
        {
            'city': k[0],
            'state': k[1],
            'country': k[2],
            'geocode_str': ', '.join(filter(None, [k[0], k[1], COUNTRY_NORMALIZE.get(k[2], k[2])])),
            'team_count': count,
            'lat': None,
            'lng': None,
        }
        for k, count in location_counter.most_common()
    ]

    out_dir = Path(path).parent
    (out_dir / 'teams_to_geocode.json').write_text(
        json.dumps(teams, indent=2, ensure_ascii=False), encoding='utf-8')
    (out_dir / 'unique_locations.json').write_text(
        json.dumps(unique_locations, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"Teams extracted:      {len(teams):,}")
    print(
        f"Unique locations:     {len(unique_locations):,}  ← this is how many geocode calls you need")
    print(f"\nFiles written to {out_dir}/")
    print("  teams_to_geocode.json")
    print("  unique_locations.json")
    print("\nNext step: run geocode.py on unique_locations.json")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_teams.py <path/to/ftc_teams_raw.json>")
        sys.exit(1)
    main(sys.argv[1])
