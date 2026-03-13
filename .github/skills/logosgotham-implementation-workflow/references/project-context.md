# Project Context

## Primary Docs

- `design.md`: architecture, layered system design, and intended end-to-end behavior
- `requirements.md`: product requirements and acceptance criteria
- `tasks.md`: implementation plan broken into layered tasks
- `frontend/docs/Agents.md`: frontend payload contracts, UI rules, and demo behavior
- `requirements.txt`: Python dependencies
- `frontend/package.json`: frontend scripts and dependencies

Treat `design.md`, `requirements.md`, and `tasks.md` as authoritative inputs for implementation and validation. Do not edit them unless the user explicitly asks.

## Repo Shape

- `backend/main.py`: FastAPI app, in-memory state, WebSocket broadcast, demo pipeline trigger
- `backend/services/`: layered backend implementation
- `backend/agents/agent_orchestrator.py`: agent workflow entrypoint
- `backend/models/schema.py`: Pydantic/domain schemas
- `tests/test_scenarios.py`: current test surface
- `frontend/src/app/`: Next.js app shell
- `frontend/src/components/`: tactical UI components
- `frontend/src/store/useLogisticsStore.ts`: shared logistics state

## Current Tooling

### Backend

- Frameworks: FastAPI, Pydantic, LangGraph, LangChain Groq
- Likely startup command: `uvicorn backend.main:app --reload`
- Test surface: `pytest`

### Frontend

- Frameworks: Next.js 16, React 19, TypeScript, Zustand, Cesium, Resium
- Scripts:
  - `npm run dev`
  - `npm run build`
  - `npm run lint`

## Integration Flow To Preserve

1. Frontend action or backend signal trigger
2. Backend ingestion or orchestration step
3. Agent or service processing
4. State update and WebSocket/API broadcast
5. Frontend state refresh and UI/map update
6. User inspection of the running app

## Working Conventions Inferred From Docs

- The project is requirement-driven; acceptance criteria matter more than ad hoc implementation preferences.
- The backend is layered around ingestion, processing, knowledge, and agent orchestration.
- The frontend is a tactical command-center UI, not a generic dashboard.
- Backend agent payloads drive frontend state and map behavior.
- Prototype/demo flow is important, including mockable or in-memory behavior.

## Recommended Change Order

1. Requirements and affected task item
2. Schema or payload contract if needed
3. Backend producer logic
4. Frontend store/consumer logic
5. UI presentation
6. Verification