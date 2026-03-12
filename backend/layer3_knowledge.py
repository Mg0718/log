from __future__ import annotations

from typing import Any

import requests

try:
    from shapely.geometry import LineString, Point
except Exception:
    LineString = None
    Point = None


CITY_COORDS = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
    "Kolkata": (22.5726, 88.3639),
    "Guwahati": (26.1445, 91.7362),
}


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
