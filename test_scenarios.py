from __future__ import annotations

import json

from main import run_pipeline


def run_scenarios() -> None:
    scenarios = [
        {
            "name": "Active Flood",
            "payload": {
                "signal_text": "Active severe flood near West India Corridor causing road closures now.",
                "shipment": {
                    "shipment_id": "SHP-001",
                    "origin": "Mumbai",
                    "destination": "Delhi",
                    "current_location": "Vadodara",
                    "route_region": "West India Corridor",
                    "mode": "road",
                    "priority": 4,
                    "remaining_distance_km": 850,
                    "route_overlap": 0.95,
                    "fuel_rate": 2.6,
                    "penalty_rate": 140.0,
                    "original_eta_hours": 18.0,
                    "base_fuel_distance_km": 850,
                },
            },
        },
        {
            "name": "Predictive Cyclone",
            "payload": {
                "signal_text": "Major cyclone expected in East Coast Corridor in 6 hours with severe highway disruption risk.",
                "shipment": {
                    "shipment_id": "SHP-002",
                    "origin": "Chennai",
                    "destination": "Visakhapatnam",
                    "current_location": "Nellore",
                    "route_region": "East Coast Corridor",
                    "mode": "road",
                    "priority": 5,
                    "remaining_distance_km": 610,
                    "route_overlap": 0.9,
                    "fuel_rate": 2.9,
                    "penalty_rate": 160.0,
                    "original_eta_hours": 14.0,
                    "base_fuel_distance_km": 610,
                },
            },
        },
        {
            "name": "Port Congestion",
            "payload": {
                "signal_text": "Critical port congestion at Jawaharlal Nehru Port impacting vessel berthing operations now.",
                "shipment": {
                    "shipment_id": "SHP-003",
                    "origin": "Nhava Sheva",
                    "destination": "Dubai",
                    "current_location": "Jawaharlal Nehru Port",
                    "route_region": "Jawaharlal Nehru Port",
                    "mode": "sea",
                    "priority": 3,
                    "remaining_distance_km": 1450,
                    "route_overlap": 0.85,
                    "fuel_rate": 4.1,
                    "penalty_rate": 220.0,
                    "original_eta_hours": 42.0,
                    "base_fuel_distance_km": 1450,
                },
            },
        },
    ]

    for scenario in scenarios:
        result = run_pipeline(scenario["payload"])
        print(f"\n=== {scenario['name']} ===")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run_scenarios()
