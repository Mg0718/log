# Project Aegis Layer 4 Requirements

## Runtime
- Python 3.10+
- LangGraph for orchestration
- LangChain + Groq for optional fast structured extraction
- Pydantic for strict typed interfaces

## Python Dependencies
- `langgraph`
- `langchain`
- `langchain-groq`
- `pydantic`

Install with:

```bash
pip install -r requirements.txt
```

## Environment Variables

### Required for LLM parsing
- `GROQ_API_KEY`: API key for Groq access

### Optional
- `GROQ_MODEL`: overrides the default model. Default is `llama-3.3-70b-versatile` in the parser helper.

## Files for Integration

### For Member 1
- Use `schema.py` for the canonical payload shapes.
- If upstream sends raw external signal text, call `parse_disruption_text()` from `skills/signal_processor.py`.
- If upstream already has structured disruption JSON, ensure it matches the `Disruption` schema exactly.

### For Member 3
- Consume the final payload produced by `run_decision_engine()` in `main.py`.
- The UI contract is the serialized `FinalDecision` model.
- Relevant keys:
  - `shipment_id`
  - `disruption_id`
  - `action_type`
  - `recommended_mode`
  - `business_impact_score`
  - `route_option`
  - `cost_summary`
  - `reasoning_log`

## Demo Execution

Run the provided scenarios:

```bash
python test_scenarios.py
```

## Reliability Notes
- The signal processor uses the Groq LLM when configured.
- If the API key is missing or parsing fails, a heuristic fallback parser is used.
- The routing engine is mocked for hackathon speed and deterministic demo behavior.
