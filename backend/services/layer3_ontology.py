"""
Layer 3 — NetworkX Ontology Graph (logistics digital twin).

Mirrors the architecture diagram ontology:
  Shipment ──travels_through──► Route ──has_segment──► Segment
  Shipment ──managed_by──────► Carrier
  Port ──────────────────────► WeatherEvent
  DisruptionZone ──at_risk_from──► Shipment
  Route ──intersects──────────► DisruptionZone

Key behaviour:
  When add_disruption_zone() is called, the graph AUTOMATICALLY runs the query
  "Which shipments intersect this polygon?"
  and adds at_risk_from edges to the graph — no manual call required.

Spatial computation: Shapely (with degree-based proximity fallback).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False
    logger.error("networkx not installed — OntologyGraph will be non-functional")

try:
    from shapely.geometry import LineString, Point
    _HAS_SHAPELY = True
except ImportError:
    _HAS_SHAPELY = False


class OntologyGraph:
    """
    NetworkX DiGraph representing the live logistics network.

    Node types (node_type attribute):
        Shipment       — tracked cargo unit
        Route          — OSRM-computed polyline
        Segment        — individual road segment
        DisruptionZone — geospatial hazard polygon
        Port           — major logistics port
        Carrier        — transport company
        WeatherEvent   — transient weather alert

    Edge relations (rel attribute):
        travels_through, has_segment, intersects,
        at_risk_from, managed_by, linked_weather
    """

    def __init__(self) -> None:
        self.G: Any = nx.DiGraph() if _HAS_NX else None
        logger.info("OntologyGraph initialised (NetworkX DiGraph)" if _HAS_NX else
                    "OntologyGraph unavailable — networkx missing")

    # ──────────────────────────────────────────────────────
    # Node builders
    # ──────────────────────────────────────────────────────

    def add_shipment(self, shipment: dict) -> None:
        if not _HAS_NX:
            return
        sid     = shipment["id"]
        details = shipment.get("shipment_details", {})
        self.G.add_node(
            sid,
            node_type="Shipment",
            origin=details.get("origin", ""),
            destination=details.get("destination", ""),
            mode=details.get("mode", "road"),
            current_lat=shipment.get("currentLat", 0.0),
            current_lon=shipment.get("currentLon", 0.0),
            route=shipment.get("currentRoute", []),   # [(lon, lat), ...]
            risk_score=shipment.get("riskScore", 0),
            status="in_transit",
        )
        # Route node
        route_id = f"ROUTE-{sid}"
        self.G.add_node(
            route_id,
            node_type="Route",
            waypoints=shipment.get("currentRoute", []),
        )
        self.G.add_edge(sid, route_id, rel="travels_through")

        # Segment nodes mirror the Route -> Segment relation in the architecture.
        route_coords = shipment.get("currentRoute", [])
        for idx in range(max(0, len(route_coords) - 1)):
            try:
                start = route_coords[idx]
                end = route_coords[idx + 1]
                seg_id = f"SEG-{sid}-{idx + 1}"
                self.G.add_node(
                    seg_id,
                    node_type="Segment",
                    start_lon=float(start[0]),
                    start_lat=float(start[1]),
                    end_lon=float(end[0]),
                    end_lat=float(end[1]),
                )
                self.G.add_edge(route_id, seg_id, rel="has_segment")
            except Exception:
                continue

        # Carrier node (one per mode for demo)
        carrier_id = f"CARRIER-{details.get('mode', 'road').upper()}"
        if not self.G.has_node(carrier_id):
            self.G.add_node(carrier_id, node_type="Carrier", mode=details.get("mode", "road"))
        self.G.add_edge(sid, carrier_id, rel="managed_by")

    def add_port(self, port: dict) -> None:
        if not _HAS_NX:
            return
        pid = port["name"]
        self.G.add_node(pid, node_type="Port", lat=port["lat"], lon=port["lon"])

    def add_weather_event(self, event: dict) -> None:
        if not _HAS_NX:
            return
        eid = f"WEATHER-{event.get('location', 'unknown').replace(' ', '_').upper()}"
        self.G.add_node(
            eid,
            node_type="WeatherEvent",
            event_type=event.get("type", ""),
            severity=event.get("severity", 5),
            lat=event.get("lat", 0.0),
            lon=event.get("lon", 0.0),
        )

        # Link nearby ports to weather event to represent Port -> WeatherEvent relation.
        try:
            event_lat = float(event.get("lat", 0.0))
            event_lon = float(event.get("lon", 0.0))
            for node_id, data in self.G.nodes(data=True):
                if data.get("node_type") != "Port":
                    continue
                try:
                    port_lat = float(data.get("lat", 0.0))
                    port_lon = float(data.get("lon", 0.0))
                except Exception:
                    continue

                # Approximate "nearby" threshold (about 200 km in latitude terms).
                if abs(port_lat - event_lat) <= 2.0 and abs(port_lon - event_lon) <= 2.0:
                    self.G.add_edge(node_id, eid, rel="linked_weather")
        except Exception:
            pass

    def add_disruption_zone(self, disruption: dict) -> list[str]:
        """
        Add a DisruptionZone node and AUTO-TRIGGER the intersection query:
            "Which shipments intersect this polygon?"

        Returns list of at-risk shipment IDs (edges added automatically).
        """
        if not _HAS_NX:
            return []

        did = disruption["id"]
        self.G.add_node(
            did,
            node_type="DisruptionZone",
            disruption_type=disruption.get("type", ""),
            severity=disruption.get("severity", 5),
            lat=disruption.get("lat", 0.0),
            lon=disruption.get("lon", 0.0),
            radius_km=disruption.get("radius_km", 25.0),
            polygon=disruption.get("polygonGeoJSON", []),
        )

        # ─── AUTO-TRIGGER: Which shipments intersect this polygon? ───────────
        logger.info(
            f"OntologyGraph: DisruptionZone {did} added — auto-querying intersecting shipments"
        )
        at_risk_ids = self._query_intersecting_shipments(disruption)

        for shipment_id in at_risk_ids:
            self.G.add_edge(did, shipment_id, rel="at_risk_from")
            # Also add intersects edge from route to disruption
            route_id = f"ROUTE-{shipment_id}"
            if self.G.has_node(route_id):
                self.G.add_edge(route_id, did, rel="intersects")
            # Raise risk score in node
            if self.G.has_node(shipment_id):
                prev = self.G.nodes[shipment_id].get("risk_score", 0)
                self.G.nodes[shipment_id]["risk_score"] = max(prev, 80)
            logger.info(f"  → {did} at_risk_from → {shipment_id}")

        return at_risk_ids

    def update_shipment_position(self, shipment_id: str, lat: float, lon: float) -> None:
        if _HAS_NX and self.G.has_node(shipment_id):
            self.G.nodes[shipment_id]["current_lat"] = lat
            self.G.nodes[shipment_id]["current_lon"] = lon

    def update_shipment_route(self, shipment_id: str, route: list) -> None:
        if not _HAS_NX:
            return
        if self.G.has_node(shipment_id):
            self.G.nodes[shipment_id]["route"] = route
        route_id = f"ROUTE-{shipment_id}"
        if self.G.has_node(route_id):
            self.G.nodes[route_id]["waypoints"] = route

    # ──────────────────────────────────────────────────────
    # Spatial Queries
    # ──────────────────────────────────────────────────────

    def _query_intersecting_shipments(self, disruption: dict) -> list[str]:
        """
        Geospatial query: find all Shipment nodes whose route polylines
        intersect the circular disruption zone.
        Uses Shapely when available; falls back to point proximity check.
        """
        dis_lat    = float(disruption.get("lat", 0.0))
        dis_lon    = float(disruption.get("lon", 0.0))
        radius_km  = float(disruption.get("radius_km", 25.0))
        radius_deg = radius_km / 111.0

        at_risk: list[str] = []
        for nid, data in self.G.nodes(data=True):
            if data.get("node_type") != "Shipment":
                continue
            route = data.get("route", [])
            if self._route_intersects(route, dis_lon, dis_lat, radius_deg):
                at_risk.append(nid)
        return at_risk

    def _route_intersects(
        self,
        route: list,
        dis_lon: float,
        dis_lat: float,
        radius_deg: float,
    ) -> bool:
        if not route:
            return False

        if _HAS_SHAPELY:
            try:
                hazard = Point(dis_lon, dis_lat).buffer(radius_deg)
                line   = LineString([(float(c[0]), float(c[1])) for c in route])
                return bool(line.intersects(hazard))
            except Exception:
                pass

        # Fallback: point proximity check along route
        for coord in route:
            try:
                lon, lat = float(coord[0]), float(coord[1])
                if ((lon - dis_lon) ** 2 + (lat - dis_lat) ** 2) ** 0.5 <= radius_deg:
                    return True
            except Exception:
                continue
        return False

    # ──────────────────────────────────────────────────────
    # Graph Queries
    # ──────────────────────────────────────────────────────

    def get_active_shipments(self) -> list[dict]:
        if not _HAS_NX:
            return []
        return [
            {"id": nid, **data}
            for nid, data in self.G.nodes(data=True)
            if data.get("node_type") == "Shipment"
        ]

    def get_active_disruptions(self) -> list[dict]:
        if not _HAS_NX:
            return []
        return [
            {"id": nid, **data}
            for nid, data in self.G.nodes(data=True)
            if data.get("node_type") == "DisruptionZone"
        ]

    def get_at_risk_shipments(self, disruption_id: str) -> list[str]:
        """Return shipment IDs linked by at_risk_from edges from a disruption."""
        if not _HAS_NX or not self.G.has_node(disruption_id):
            return []
        return [
            target
            for _, target, data in self.G.out_edges(disruption_id, data=True)
            if data.get("rel") == "at_risk_from"
        ]

    def summary(self) -> dict:
        if not _HAS_NX:
            return {}
        node_counts: dict[str, int] = {}
        for _, data in self.G.nodes(data=True):
            t = data.get("node_type", "unknown")
            node_counts[t] = node_counts.get(t, 0) + 1
        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "node_types": node_counts,
        }


# Module-level singleton shared across the app
ontology_graph = OntologyGraph()
