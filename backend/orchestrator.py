from __future__ import annotations

import json

from layer1_ingestion import get_raw_signals
from layer2_processing import SignalProcessor
from layer3_knowledge import ShipmentKnowledgeModel


def run_pipeline() -> dict:
    processor = SignalProcessor()
    knowledge_model = ShipmentKnowledgeModel()

    payload = {"results": []}

    try:
        raw_signals = get_raw_signals()
    except Exception:
        raw_signals = []

    for raw_signal in raw_signals:
        try:
            disruption = processor.process_signal(raw_signal)
            affected_shipments = knowledge_model.find_at_risk_shipments(disruption)

            for shipment in affected_shipments:
                payload["results"].append(
                    {
                        "disruption": disruption,
                        "shipment_data": shipment["shipment_data"],
                    }
                )
        except Exception:
            continue

    return payload


if __name__ == "__main__":
    print(json.dumps(run_pipeline(), indent=2))
