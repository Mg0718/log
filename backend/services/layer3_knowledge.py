from __future__ import annotations

import logging
from typing import Any

import requests

try:
    import h3
except Exception:
    h3 = None  # type: ignore[assignment]

try:
    from shapely.geometry import LineString, Point, Polygon
except Exception:
    LineString = None  # type: ignore[assignment]
    Point = None  # type: ignore[assignment]
    Polygon = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

CITY_COORDS: dict[str, tuple[float, float]] = {
    # ── Metros ──────────────────────────────────────────────────────────────────
    "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Bombay": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Madras": (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
    "Bengaluru": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
    "Calcutta": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Pune": (18.5204, 73.8567),
    # ── South India ─────────────────────────────────────────────────────────────
    "Madurai": (9.9252, 78.1198),
    "Coimbatore": (11.0168, 76.9558),
    "Salem": (11.6643, 78.1460),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Trichy": (10.7905, 78.7047),
    "Tirunelveli": (8.7139, 77.7567),
    "Kochi": (9.9312, 76.2673),
    "Ernakulam": (9.9312, 76.2673),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Trivandrum": (8.5241, 76.9366),
    "Kozhikode": (11.2588, 75.7804),
    "Calicut": (11.2588, 75.7804),
    "Mangalore": (12.9141, 74.8560),
    "Mysore": (12.2958, 76.6394),
    "Mysuru": (12.2958, 76.6394),
    "Hubli": (15.3647, 75.1240),
    "Dharwad": (15.4589, 75.0078),
    "Nellore": (14.4426, 79.9865),
    "Visakhapatnam": (17.6868, 83.2185),
    "Vizag": (17.6868, 83.2185),
    "Vijayawada": (16.5062, 80.6480),
    "Guntur": (16.3067, 80.4365),
    "Tirupati": (13.6288, 79.4192),
    "Warangal": (17.9784, 79.5941),
    # ── North & Central India ────────────────────────────────────────────────────
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Varanasi": (25.3176, 82.9739),
    "Agra": (27.1767, 78.0081),
    "Allahabad": (25.4358, 81.8463),
    "Prayagraj": (25.4358, 81.8463),
    "Bhopal": (23.2599, 77.4126),
    "Indore": (22.7196, 75.8577),
    "Nagpur": (21.1458, 79.0882),
    "Patna": (25.5941, 85.1376),
    "Ranchi": (23.3441, 85.3096),
    "Raipur": (21.2514, 81.6296),
    # ── West India ──────────────────────────────────────────────────────────────
    "Vadodara": (22.3072, 73.1812),
    "Baroda": (22.3072, 73.1812),
    "Surat": (21.1702, 72.8311),
    "Rajkot": (22.3039, 70.8022),
    "Nashik": (19.9975, 73.7898),
    "Aurangabad": (19.8762, 75.3433),
    "Solapur": (17.6805, 75.9064),
    # ── East & North-East India ──────────────────────────────────────────────────
    "Guwahati": (26.1445, 91.7362),
    "Bhubaneswar": (20.2961, 85.8245),
    "Cuttack": (20.4625, 85.8828),
    "Vijaywada": (16.5062, 80.6480),
    # ── Port Cities & Logistics Hubs ────────────────────────────────────────────
    "Ennore": (13.2174, 80.3337),
    "Nhava Sheva": (18.9499, 72.9497),
    "Mundra": (22.8396, 69.7039),
    "Haldia": (22.0257, 88.0583),
    "Tuticorin": (8.7642, 78.1348),
    "Thoothukudi": (8.7642, 78.1348),
    # ── Tier-2 / Logistics Corridors ────────────────────────────────────────────
    "Ludhiana": (30.9010, 75.8573),
    "Amritsar": (31.6340, 74.8723),
    "Chandigarh": (30.7333, 76.7794),
    "Dehradun": (30.3165, 78.0322),
    "Jodhpur": (26.2389, 73.0243),
    "Udaipur": (24.5854, 73.7125),
    "Kota": (25.2138, 75.8648),
    "Gwalior": (26.2183, 78.1828),
    "Jabalpur": (23.1815, 79.9864),
    "Bilaspur": (22.0796, 82.1391),
    "Vizianagaram": (18.1066, 83.3956),
    "Rajahmundry": (17.0005, 81.8040),
    "Dhanbad": (23.7957, 86.4304),
    "Jamshedpur": (22.8046, 86.2029),
}

# Build a lowercase-keyed index for case-insensitive lookup
_CITY_LOWER: dict[str, tuple[float, float]] = {k.lower(): v for k, v in CITY_COORDS.items()}


def get_city_coords_or_none(city_name: str) -> tuple[float, float] | None:
    """Return (lat, lon) for city_name (case-insensitive) or None if unknown."""
    return _CITY_LOWER.get(city_name.strip().lower())


def list_known_cities() -> list[str]:
    """Return the canonical list of city names the system understands."""
    seen: set[tuple[float, float]] = set()
    result: list[str] = []
    for name, coords in CITY_COORDS.items():
        if coords not in seen:
            seen.add(coords)
            result.append(name)
    return sorted(result)


class ShipmentKnowledgeModel:
    def __init__(self) -> None:
        self.shipments = [
            {
                "shipment_id": "S101",
                "origin": "Delhi",
                "destination": "Mumbai",
                "priority": "High",
                "mode": "road",
                "priority_score": 5,
                "fuel_rate": 2.8,
                "penalty_rate": 180.0,
            },
            {
                "shipment_id": "S102",
                "origin": "Chennai",
                "destination": "Bangalore",
                "priority": "Medium",
                "mode": "road",
                "priority_score": 3,
                "fuel_rate": 2.5,
                "penalty_rate": 130.0,
            },
            {
                "shipment_id": "S103",
                "origin": "Kolkata",
                "destination": "Guwahati",
                "priority": "Low",
                "mode": "road",
                "priority_score": 2,
                "fuel_rate": 2.3,
                "penalty_rate": 100.0,
            },
        ]

    def _get_city_coords(self, city_name: str) -> tuple[float, float]:
        """Case-insensitive lookup. Falls back to centre of India only as last resort."""
        result = get_city_coords_or_none(city_name)
        if result is not None:
            return result
        # Partial match: try if any known city name starts with the input
        lower = city_name.strip().lower()
        for key, coords in _CITY_LOWER.items():
            if key.startswith(lower) or lower.startswith(key):
                return coords
        logger.warning("Unknown city '%s' — falling back to centre of India", city_name)
        return (20.5937, 78.9629)

    def fetch_osrm_route(self, start_coord: tuple[float, float], end_coord: tuple[float, float]) -> list[tuple[float, float]]:
        start_lat, start_lon = start_coord
        end_lat, end_lon = end_coord
        url = (
            "http://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        )
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            payload = response.json()
            routes = payload.get("routes", [])
            if routes:
                coordinates = routes[0].get("geometry", {}).get("coordinates", [])
                if coordinates:
                    return [(float(lon), float(lat)) for lon, lat in coordinates]
        except Exception:
            pass
        return [(float(start_lon), float(start_lat)), (float(end_lon), float(end_lat))]

    def find_at_risk_shipments(self, disruption_obj: dict[str, Any]) -> list[dict[str, Any]]:
        affected_shipments: list[dict[str, Any]] = []

        try:
            disruption_lon = float(disruption_obj.get("lon", 0.0))
            disruption_lat = float(disruption_obj.get("lat", 0.0))
            radius_km = float(disruption_obj.get("radius_km", 10.0))
        except Exception:
            disruption_lon = 0.0
            disruption_lat = 0.0
            radius_km = 10.0

        radius_in_degrees = radius_km / 111.0

        for shipment in self.shipments:
            try:
                start_coord = CITY_COORDS[shipment["origin"]]
                end_coord = CITY_COORDS[shipment["destination"]]
                route_coords = self.fetch_osrm_route(start_coord, end_coord)
                route_intersects = self._route_intersects_disruption(
                    route_coords=route_coords,
                    disruption_lon=disruption_lon,
                    disruption_lat=disruption_lat,
                    radius_in_degrees=radius_in_degrees,
                )

                if route_intersects:
                    origin_lat, origin_lon = start_coord  # (lat, lon)
                    affected_shipments.append(
                        {
                            "shipment_id": shipment["shipment_id"],
                            "priority": shipment["priority"],
                            "disruption": disruption_obj,
                            "shipment_data": {
                                "shipment_id": shipment["shipment_id"],
                                "origin": shipment["origin"],
                                "destination": shipment["destination"],
                                "current_location": shipment["origin"],
                                # Real GPS coordinates of the truck (at its origin city)
                                "current_lat": origin_lat,
                                "current_lon": origin_lon,
                                "route_region": disruption_obj.get("type", "Unknown Region"),
                                "mode": shipment["mode"],
                                "priority": shipment["priority_score"],
                                "remaining_distance_km": 350.0 if shipment["shipment_id"] == "S102" else 1200.0,
                                "route_overlap": 0.9,
                                "fuel_rate": shipment["fuel_rate"],
                                "penalty_rate": shipment["penalty_rate"],
                                "original_eta_hours": 8.0 if shipment["shipment_id"] == "S102" else 26.0,
                                "base_fuel_distance_km": 350.0 if shipment["shipment_id"] == "S102" else 1200.0,
                            },
                        }
                    )
            except Exception:
                continue

        return affected_shipments

    def calculate_geospatial_risk(
        self,
        route_coords: list[tuple[float, float]],
        disruption_polygon: list[list[float]],
        severity: float,
        urgency_weight: float = 1.0,
    ) -> dict:
        """
        Geospatial Matching Engine — Layer 4.

        Runs exact Shapely intersection math:
            risk_score = severity * overlap_percentage * urgency_weight

        Returns {"at_risk": bool, "overlap_percent": float, "final_risk_score": int}
        where final_risk_score is normalised to a 0–100 scale.
        """
        if not route_coords or len(disruption_polygon) < 3:
            return {"at_risk": False, "overlap_percent": 0.0, "final_risk_score": 0}

        try:
            h3_resolution = 7
            route_h3_cells = self._h3_route_cells(route_coords, resolution=h3_resolution)
            hazard_h3_cells = self._h3_polygon_cells(disruption_polygon, resolution=h3_resolution)

            # H3 fast pre-check: if no shared hexes, skip expensive geometry intersection.
            if route_h3_cells and hazard_h3_cells and not (route_h3_cells & hazard_h3_cells):
                return {
                    "at_risk": False,
                    "overlap_percent": 0.0,
                    "final_risk_score": 0,
                    "h3_overlap_cells": 0,
                }

            if LineString is None or Polygon is None:
                # Shapely unavailable — fall back to centroid boolean check
                cx = sum(p[0] for p in disruption_polygon) / len(disruption_polygon)
                cy = sum(p[1] for p in disruption_polygon) / len(disruption_polygon)
                radius = 0.5
                hit = self._fallback_intersection(route_coords, cx, cy, radius)
                fallback_score = min(round((severity * 0.5 * urgency_weight / 15) * 100), 100)
                h3_overlap = len(route_h3_cells & hazard_h3_cells) if (route_h3_cells and hazard_h3_cells) else 0
                return {
                    "at_risk": hit,
                    "overlap_percent": 50.0 if hit else 0.0,
                    "final_risk_score": fallback_score if hit else 0,
                    "h3_overlap_cells": h3_overlap,
                }

            route = LineString(route_coords)
            storm_zone = Polygon([(float(p[0]), float(p[1])) for p in disruption_polygon])

            if not route.intersects(storm_zone):
                return {"at_risk": False, "overlap_percent": 0.0, "final_risk_score": 0}

            affected_segment = route.intersection(storm_zone)
            overlap_pct = (
                affected_segment.length / route.length if route.length > 0 else 0.0
            )

            # Formula:  severity * overlap% * urgency_weight  →  normalise to 100
            raw_score = severity * overlap_pct * urgency_weight
            normalized = min(round((raw_score / 15) * 100), 100)
            h3_overlap = len(route_h3_cells & hazard_h3_cells) if (route_h3_cells and hazard_h3_cells) else 0

            return {
                "at_risk": True,
                "overlap_percent": round(overlap_pct * 100, 1),
                "final_risk_score": normalized,
                "h3_overlap_cells": h3_overlap,
            }
        except Exception as exc:
            logger.warning("calculate_geospatial_risk failed: %s", exc)
            return {"at_risk": False, "overlap_percent": 0.0, "final_risk_score": 0}

    def _h3_polygon_cells(self, polygon_coords: list[list[float]], resolution: int = 7) -> set[str]:
        if h3 is None or len(polygon_coords) < 3:
            return set()

        try:
            # Input polygon is [lon, lat]; H3 expects (lat, lon).
            latlng_ring = [(float(pt[1]), float(pt[0])) for pt in polygon_coords]

            # h3-py v4 API
            if hasattr(h3, "LatLngPoly") and hasattr(h3, "polygon_to_cells"):
                poly = h3.LatLngPoly(latlng_ring)
                return set(h3.polygon_to_cells(poly, resolution))

            # h3-py v3 API fallback
            if hasattr(h3, "polyfill"):
                geojson = {
                    "type": "Polygon",
                    "coordinates": [polygon_coords],
                }
                return set(h3.polyfill(geojson, resolution, geo_json_conformant=True))
        except Exception:
            return set()

        return set()

    def _h3_route_cells(self, route_coords: list[tuple[float, float]], resolution: int = 7) -> set[str]:
        if h3 is None or not route_coords:
            return set()

        cells: set[str] = set()
        try:
            for lon, lat in route_coords:
                # h3-py v4 API
                if hasattr(h3, "latlng_to_cell"):
                    cells.add(h3.latlng_to_cell(float(lat), float(lon), resolution))
                # h3-py v3 API fallback
                elif hasattr(h3, "geo_to_h3"):
                    cells.add(h3.geo_to_h3(float(lat), float(lon), resolution))
        except Exception:
            return set()

        return cells

    def _route_intersects_disruption(
        self,
        route_coords: list[tuple[float, float]],
        disruption_lon: float,
        disruption_lat: float,
        radius_in_degrees: float,
    ) -> bool:
        try:
            if Point is not None and LineString is not None:
                disruption_polygon = Point(disruption_lon, disruption_lat).buffer(radius_in_degrees)
                route = LineString(route_coords)
                return bool(route.intersects(disruption_polygon))
        except Exception:
            pass

        return self._fallback_intersection(route_coords, disruption_lon, disruption_lat, radius_in_degrees)

    def _fallback_intersection(
        self,
        route_coords: list[tuple[float, float]],
        disruption_lon: float,
        disruption_lat: float,
        radius_in_degrees: float,
    ) -> bool:
        try:
            for lon, lat in route_coords:
                if ((lon - disruption_lon) ** 2 + (lat - disruption_lat) ** 2) ** 0.5 <= radius_in_degrees:
                    return True

            start_lon, start_lat = route_coords[0]
            end_lon, end_lat = route_coords[-1]
            sample_points = 12
            for idx in range(sample_points + 1):
                ratio = idx / sample_points
                lon = start_lon + ((end_lon - start_lon) * ratio)
                lat = start_lat + ((end_lat - start_lat) * ratio)
                if ((lon - disruption_lon) ** 2 + (lat - disruption_lat) ** 2) ** 0.5 <= radius_in_degrees:
                    return True
        except Exception:
            return False

        return False
