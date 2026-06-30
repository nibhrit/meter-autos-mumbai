"""
Curated Mumbai routes with baked-in distances (km), standing in for live
geocoding per v1 scope. Distances are reasonable real-world approximations
for these well-known origin/destination pairs, not measured live.

`zone_restricted=True` marks routes that enter the no-auto zone: autos
are banned south of the Bandra (W) Fire Station / Sion Bus Depot line,
i.e. all of South Mumbai / the Island City (Worli, Lower Parel, Fort,
Colaba, Churchgate, CST, Marine Lines, etc).
"""

from dataclasses import dataclass


@dataclass
class Route:
    id: str
    origin: str
    destination: str
    distance_km: float
    zone_restricted: bool  # True = destination/route is in the no-auto zone


PRESET_ROUTES: dict[str, Route] = {
    r.id: r for r in [
        Route("andheri_versova", "Andheri Station", "Versova", 3.2, False),
        Route("bandra_bkc", "Bandra Station", "BKC", 4.0, False),
        Route("kurla_powai", "Kurla Station", "Powai", 7.5, False),
        Route("andheri_borivali", "Andheri Station", "Borivali", 12.5, False),
        Route("goregaon_malad", "Goregaon", "Malad", 3.8, False),
        Route("vileparle_airport", "Vile Parle", "Airport T2", 5.0, False),
        Route("mulund_thane", "Mulund", "Thane", 6.0, False),
        Route("powai_chembur", "Powai", "Chembur", 9.0, False),
        Route("dadar_worli", "Dadar", "Worli", 5.0, True),
        Route("cst_colaba", "CST", "Colaba", 3.5, True),
        Route("bandra_fort", "Bandra Station", "Fort", 14.0, True),
    ]
}


def get_route(route_id: str) -> Route:
    if route_id not in PRESET_ROUTES:
        raise ValueError(f"Unknown route_id: {route_id}")
    return PRESET_ROUTES[route_id]


def list_routes() -> list[dict]:
    return [
        {"id": r.id, "label": f"{r.origin} -> {r.destination}", "distance_km": r.distance_km,
         "zone_restricted": r.zone_restricted}
        for r in PRESET_ROUTES.values()
    ]
