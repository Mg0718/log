"""Quick smoke tests for Layer 1-3 new services."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.services.layer2_rag import rag_processor
from backend.services.layer3_ontology import OntologyGraph
from backend.services.layer3_knowledge import ShipmentKnowledgeModel
from backend.services.event_stream import EventStream

def test_rag_extraction():
    sig = {"source": "gdelt_news", "raw_text": "Heavy flooding on NH48 near Chennai halts truck traffic"}
    result = rag_processor.extract(sig)
    assert result is not None
    assert result["type"] == "flooding"
    assert abs(result["lat"] - 13.08) < 1.0
    print(f"  RAG → type={result['type']} lat={result['lat']} lon={result['lon']} sev={result['severity']}")

def test_rag_port_signal():
    sig = {"source": "gocomet_port", "raw_text": "Port congestion at JNPT Mumbai vessel delays", "lat": 18.9498, "lon": 72.9508}
    result = rag_processor.extract(sig)
    assert result is not None
    assert result["type"] == "port_congestion"
    assert result["lat"] == 18.9498
    print(f"  RAG → type={result['type']} lat={result['lat']} lon={result['lon']}")

def test_ontology_auto_trigger():
    g = OntologyGraph()
    ship = {
        "id": "S-CHENNAI",
        "currentRoute": [[80.27, 13.08], [77.59, 12.97]],
        "currentLat": 13.08,
        "currentLon": 80.27,
        "riskScore": 0,
        "shipment_details": {"origin": "Chennai", "destination": "Bangalore", "mode": "road"},
    }
    g.add_shipment(ship)
    assert len(g.get_active_shipments()) == 1
    print(f"  Graph seeded: {g.summary()}")

    disruption = {
        "id": "EVT-001",
        "type": "FLOODING",
        "lat": 13.08,
        "lon": 80.27,
        "radius_km": 35.0,
        "severity": 8,
        "polygonGeoJSON": [],
    }
    at_risk = g.add_disruption_zone(disruption)
    print(f"  Auto-query result: {at_risk}")
    assert "S-CHENNAI" in at_risk, "Ontology should flag S-CHENNAI as at-risk"
    print(f"  Graph after disruption: {g.summary()}")
    assert g.summary()["total_edges"] >= 2      # travels_through + at_risk_from + managed_by

def test_event_stream():
    import asyncio
    stream = EventStream()
    async def _run():
        await stream.publish({"source": "test", "raw_text": "test signal"})
        batch = await stream.consume_batch(max_count=5)
        assert len(batch) == 1
        assert batch[0]["source"] == "test"
        print(f"  EventStream ({stream.backend}): publish + consume OK")
    asyncio.run(_run())


def test_geospatial_matching_engine_formula():
    model = ShipmentKnowledgeModel()
    route = [(79.8, 12.5), (79.5, 12.6), (79.0, 12.8), (78.5, 12.9)]
    storm_polygon = [
        [79.6, 12.4],
        [79.6, 12.8],
        [79.2, 12.8],
        [79.2, 12.4],
        [79.6, 12.4],
    ]
    result = model.calculate_geospatial_risk(
        route_coords=route,
        disruption_polygon=storm_polygon,
        severity=8.5,
        urgency_weight=1.2,
    )
    assert result["at_risk"] is True
    assert result["overlap_percent"] > 0
    assert result["final_risk_score"] > 0
    print(
        "  Geospatial Engine -> "
        f"overlap={result['overlap_percent']}% risk={result['final_risk_score']} "
        f"h3_overlap_cells={result.get('h3_overlap_cells', 0)}"
    )

if __name__ == "__main__":
    tests = [
        ("RAG: news signal extraction",      test_rag_extraction),
        ("RAG: port signal extraction",      test_rag_port_signal),
        ("Ontology: auto-trigger query",     test_ontology_auto_trigger),
        ("EventStream: publish/consume",     test_event_stream),
        ("Layer 4: geospatial risk formula", test_geospatial_matching_engine_formula),
    ]
    passed = 0
    for name, fn in tests:
        try:
            print(f"\n[TEST] {name}")
            fn()
            print(f"  ✓ PASSED")
            passed += 1
        except Exception as exc:
            print(f"  ✗ FAILED: {exc}")

    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
