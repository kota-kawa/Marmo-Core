import sys
import json

data = json.load(sys.stdin)
p = data.get('person', {})
bp = p.get('birthPlace', {}).get('geo', {})
print(f"# Astrological Reading for {p.get('name', 'N/A')}")
print(f"**Birth Details:** {p.get('birthDate', 'N/A')} UTC, Location: {bp.get('latitude', 'N/A')}°N, {bp.get('longitude', 'N/A')}°E")

print(f"\n## Core Natal Potential (D1 Rasi Chart)")
houses = data.get('d1Chart', {}).get('houses', [])
asc_house = next((h for h in houses if h.get('number') == 1), {})
print(f"**Ascendant (Lagna):** {asc_house.get('sign', 'N/A')}")

print("\n### Planetary Placements")
for h in houses:
    occupants = h.get('occupants', [])
    for occ in occupants:
        if occ is not None and isinstance(occ, dict):
            print(f"- **{occ.get('celestialBody', 'N/A')}**: House {h.get('number', 'N/A')} - {h.get('sign', 'N/A')} ({round(occ.get('signDegrees', 0), 2)}°)")

print("\n### Panchanga")
panchanga = data.get('panchanga', {})
print(f"- **Tithi**: {panchanga.get('tithi', 'N/A')}")
print(f"- **Nakshatra**: {panchanga.get('nakshatra', 'N/A')}")
print(f"- **Yoga**: {panchanga.get('yoga', 'N/A')}")
print(f"- **Karana**: {panchanga.get('karana', 'N/A')}")
print(f"- **Vaara**: {panchanga.get('vaara', 'N/A')}")

print("\n### Dashas")
dashas = data.get('dashas', {})
print(f"- **Current Mahadasha**: {dashas.get('current_mahadasha', 'N/A')}")
print(f"- **Current Antardasha**: {dashas.get('current_antardasha', 'N/A')}")

print("\n---")
print("*Note: This is a direct extraction of your local generated chart. Advanced KP sublord data requires Python 3.11+. The script generated this reading purely using offline logic inside `jyotishganit`.*")
