"""
Free OpenStreetMap routing, replacing the 11 baked-in presets so any Mumbai
route works. No Google, no billing account, no API key:
  - Photon (photon.komoot.io)  -> geocoding / autocomplete
  - OSRM   (router.project-osrm.org) -> road-network distance

These are public community servers: great for a demo, rate-limited and not
SLA-backed for production. All calls fail soft — the caller decides what to do
when OSM is unreachable (we fall back to preset routes in the API layer).

The no-auto zone (autos banned south of the Bandra (W) / Sion line) was a
per-preset boolean in v1; with arbitrary points it becomes a point-in-polygon
test against an approximate South-Mumbai / Island-City polygon.
"""

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass

# Road distance is typically ~1.3x the straight-line distance in a dense city —
# used only when OSRM is unreachable, so we still return a usable estimate.
HAVERSINE_ROAD_FACTOR = 1.3

# Mumbai bias for geocoding, and a bounding box to drop far-away matches.
MUMBAI_LAT, MUMBAI_LON = 19.076, 72.877
MUMBAI_BBOX = (18.85, 19.30, 72.75, 73.10)  # (lat_min, lat_max, lon_min, lon_max)

USER_AGENT = "MeterAutos/1.0 (portfolio demo; https://github.com/nibhrit/meter-autos-mumbai)"
_TIMEOUT = 8

# Approximate polygon of the no-auto zone: South Mumbai / Island City, south of
# the Mahim/Bandra(W)-Sion line. Vertices are (lat, lon), tracing the island
# from Mahim (NW) across to Sion (NE), down the east side to Colaba, around the
# southern tip, and back up the west coast. Deliberately approximate — flagged
# as such in the UI.
NO_AUTO_ZONE = [
    (19.045, 72.820), (19.045, 72.880), (18.985, 72.865), (18.945, 72.850),
    (18.905, 72.830), (18.890, 72.815), (18.920, 72.805), (18.985, 72.812),
]


@dataclass
class Place:
    name: str
    label: str      # human-friendly "Name, area, city"
    lat: float
    lon: float


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _in_bbox(lat: float, lon: float) -> bool:
    la0, la1, lo0, lo1 = MUMBAI_BBOX
    return la0 <= lat <= la1 and lo0 <= lon <= lo1


def geocode(query: str, limit: int = 5) -> list[Place]:
    """Autocomplete/geocode a place name, biased to Mumbai and filtered to the region."""
    params = urllib.parse.urlencode({
        "q": query, "limit": max(limit * 2, 8), "lat": MUMBAI_LAT, "lon": MUMBAI_LON, "lang": "en",
    })
    data = _get_json(f"https://photon.komoot.io/api/?{params}")
    places = []
    for f in data.get("features", []):
        lon, lat = f["geometry"]["coordinates"]
        if not _in_bbox(lat, lon):
            continue
        p = f.get("properties", {})
        name = p.get("name") or p.get("street") or query
        bits = [b for b in (p.get("name"), p.get("suburb") or p.get("district"), p.get("city")) if b]
        label = ", ".join(dict.fromkeys(bits))  # de-dupe while preserving order
        places.append(Place(name=name, label=label or name, lat=lat, lon=lon))
        if len(places) >= limit:
            break
    return places


def _haversine_km(o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> float:
    r = 6371.0
    dlat = math.radians(d_lat - o_lat)
    dlon = math.radians(d_lon - o_lon)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(o_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.asin(math.sqrt(a))


def route_distance(o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> dict:
    """
    Road-network distance in km via OSRM, with a haversine fallback when OSRM
    is unreachable. Returns {km, source} so callers/UI can flag the estimate.
    """
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{o_lon},{o_lat};{d_lon},{d_lat}?overview=false")
    try:
        data = _get_json(url)
        if data.get("code") == "Ok" and data.get("routes"):
            return {"km": round(data["routes"][0]["distance"] / 1000, 2), "source": "osrm"}
    except Exception:
        pass
    approx = _haversine_km(o_lat, o_lon, d_lat, d_lon) * HAVERSINE_ROAD_FACTOR
    return {"km": round(approx, 2), "source": "haversine_estimate"}


def route_distance_km(o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> float:
    return route_distance(o_lat, o_lon, d_lat, d_lon)["km"]


def in_no_auto_zone(lat: float, lon: float) -> bool:
    """Ray-casting point-in-polygon against the approximate South-Mumbai zone."""
    inside = False
    n = len(NO_AUTO_ZONE)
    j = n - 1
    for i in range(n):
        yi, xi = NO_AUTO_ZONE[i]      # (lat, lon)
        yj, xj = NO_AUTO_ZONE[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


if __name__ == "__main__":
    print("Geocode 'BKC':")
    for p in geocode("BKC"):
        print(f"  {p.label}  ({p.lat}, {p.lon})  zone={in_no_auto_zone(p.lat, p.lon)}")

    print("\nGeocode 'Colaba' (should be in no-auto zone):")
    for p in geocode("Colaba", limit=2):
        print(f"  {p.label}  ({p.lat}, {p.lon})  zone={in_no_auto_zone(p.lat, p.lon)}")

    print("\nDistance Andheri Station -> BKC:")
    o = geocode("Andheri Station", limit=1)[0]
    d = geocode("BKC", limit=1)[0]
    dist = route_distance(o.lat, o.lon, d.lat, d.lon)
    print(f"  {o.label} -> {d.label}: {dist['km']} km  (source: {dist['source']})")

    print("\nZone spot-checks:")
    for name, lat, lon in [("Colaba", 18.906, 72.815), ("Andheri", 19.119, 72.846),
                            ("Fort", 18.934, 72.836), ("Powai", 19.117, 72.905)]:
        print(f"  {name}: no_auto_zone={in_no_auto_zone(lat, lon)}")
