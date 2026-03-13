---
name: logosgotham-implementation-workflow
description: 'Integrate, implement, debug, and test LogosGotham across the FastAPI backend and Next.js frontend. Use for requirement-driven feature work, end-to-end integration, WebSocket/demo flow validation, backend-agent-frontend contract alignment, and running the app for inspection without editing design.md, requirements.md, or tasks.md.'
argument-hint: 'feature, bug, integration flow, requirement, or subsystem to work on'
user-invocable: true
---

# LogosGotham Implementation Workflow

Use this skill when working on the LogosGotham hackathon project. It is optimized for tasks that touch one or more of these layers:

- FastAPI backend orchestration and API state
- Signal ingestion, processing, knowledge, and routing services
- LangGraph-style agent orchestration and recommendation flow
- Next.js frontend components, Zustand state, and Cesium visualization
- Requirement-driven implementation, integration, and verification

This skill matches the project workflow established in the conversation:

1. Explore the codebase and identify the owning backend and frontend layers.
2. Compare implementation against `design.md`, `requirements.md`, and `tasks.md` without editing those documents.
3. Fix backend blockers first when they prevent imports, API flow, orchestration, or WebSocket broadcasts.
4. Fix frontend integration points next, especially API wiring, Cesium asset handling, Zustand state updates, and reconnection behavior.
5. Run integration checks against the real app flow.
6. Start the application for user inspection when the task requires a live handoff.

## When to Use

- Add or change a feature tied to the product requirements
- Fix a defect in the backend pipeline, agent outputs, or frontend rendering
- Review whether implementation matches the requirements and task plan
- Wire new backend payloads into the tactical command-center UI
- Validate that a change preserves the prototype demo flow
- Run the backend and frontend together for end-to-end inspection

## Procedure

1. Identify the requirement and task anchor.
   - Start with [project-context.md](./references/project-context.md).
   - Treat `design.md`, `requirements.md`, and `tasks.md` as source documents unless the user explicitly asks to change them.
   - Map the request to `requirements.md` acceptance criteria and, when useful, `tasks.md` implementation tasks.
   - If the request is underspecified, state the missing assumption before editing.

2. Locate the owning layer before changing code.
   - Backend API and demo orchestration: `backend/main.py`
   - Agent pipeline: `backend/agents/`
   - Backend services and domain logic: `backend/services/`
   - Schemas and contracts: `backend/models/schema.py`
   - Frontend app shell and globe UI: `frontend/src/app/`, `frontend/src/components/`
   - Shared frontend state: `frontend/src/store/useLogisticsStore.ts`

3. Stabilize backend integration blockers first.
   - Fix import or package-structure issues that stop the backend from booting.
   - Fix syntax or orchestration issues in service or knowledge-layer files before changing UI behavior.
   - Add or repair only the endpoints needed for the target flow, such as shipment, disruption, or manual simulation endpoints.
   - Confirm the backend can broadcast the state required by the frontend.

4. Align frontend integration points with the backend.
   - Confirm environment-based API URLs and WebSocket URLs are wired correctly.
   - Fix static asset handling for Cesium when Next.js configuration blocks the map.
   - Update the store and page-level orchestration so UI actions hit the real backend instead of stale mock-only flows.
   - Preserve reconnection and state resync behavior for backend restarts.

5. Choose the implementation path.
   - If the change is data-contract or validation related, update schemas and the producer/consumer together.
   - If the change is pipeline related, preserve the staged flow: ingest signal, structure disruption, identify impacted shipments, produce recommendation payloads, update/broadcast UI state.
   - If the change is frontend only, preserve the tactical command-center aesthetic and avoid introducing generic SaaS patterns.
   - If the change spans backend and frontend, update payload shapes first, then state handling, then presentation.

6. Make the smallest coherent change set.
   - Prefer targeted edits over broad rewrites.
   - Preserve existing public payload names unless the task explicitly requires a contract change.
   - Keep backend state transitions explicit and easy to inspect.
   - Keep frontend rendering isolated from heavy Cesium reinitialization.

7. Verify behavior at the right boundary.
   - For Python logic, run or update targeted tests under `tests/` when applicable.
   - For API or orchestration changes, verify imports and runtime errors in backend entrypoints.
   - For frontend changes, run linting and confirm the affected component/store types remain valid.
   - If a requirement includes time budgets, retries, or graceful degradation, verify those behaviors directly instead of only checking happy paths.
   - For integration tasks, validate the full path: frontend action, backend endpoint or pipeline, broadcast/update mechanism, and visible UI result.

8. Run the primary end-to-end demo flow.
   - Start the backend server.
   - Start the frontend development server.
   - Validate the real-time WebSocket connection.
   - Trigger the inject-signal or equivalent simulation flow from the real UI.
   - Confirm the sequence: button click -> backend simulation -> agent pipeline -> WebSocket broadcast -> visible UI update.
   - If any step breaks, fix the earliest failing boundary first.

9. Run the application when the task calls for inspection.
   - Start the backend and frontend with the repo's actual commands.
   - Confirm that the expected end-to-end trigger works, such as the inject-signal flow or WebSocket-driven updates.
   - Leave the app in a state the user can inspect, and report any manual steps still required.

10. Close the task with requirement coverage.
   - State which requirement or task item the change satisfies.
   - Mention any remaining gaps, mock implementations, or prototype-only shortcuts.
   - Call out anything not verified, especially live API integrations or Cesium runtime behavior.

## Decision Points

- Requirements first or code first:
  Use requirements first when user intent maps to product behavior. Use code first for bug reports tied to a concrete file or runtime failure.

- Backend vs frontend ownership:
  If the issue is in payload content or sequencing, fix backend first. If payloads are already correct and only display/state behavior is wrong, fix frontend first.

- Integration blocker order:
   Resolve boot failures, import errors, syntax errors, and missing endpoints before debugging live UI behavior. Do not spend time on map rendering if the backend flow is still broken upstream.

- Prototype shortcut vs production-hardening:
  Preserve the existing prototype flow unless the user explicitly asks for stronger persistence, security, or external integration behavior.

- Tests vs lint-only verification:
  Run targeted Python tests for service/schema logic. Run frontend lint/type-oriented verification for UI/store changes when no dedicated frontend tests exist.

- Integration test depth:
   For isolated code changes, verify the touched boundary only. For user-facing flows, verify the full frontend-to-backend loop and leave the app runnable when feasible.

## Completion Checks

- The change maps to at least one requirement, task, or explicit user goal.
- Affected backend and frontend contracts stay aligned.
- New logic handles relevant failure cases, not only the happy path.
- Source documents remain unchanged unless the user explicitly requested edits to them.
- Verification was run where feasible, and any unverified surface is stated plainly.
- The result fits the repo's layered architecture instead of adding one-off logic in the wrong place.
- The live integration path was checked when the task involved app startup, WebSocket behavior, or the inject-signal demo flow.

## References

- [Project context](./references/project-context.md)
- [Integration checklist](./references/integration-checklist.md)