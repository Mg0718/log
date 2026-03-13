# Integration Checklist

Use this checklist when the request involves frontend/backend integration, demo readiness, or running the app for inspection.

## Reference Inputs

- `design.md`
- `requirements.md`
- `tasks.md`

Do not edit those files unless the user explicitly asks.

## Pre-Run Checks

1. Backend imports resolve cleanly.
2. Backend service and orchestration files have no blocking syntax errors.
3. Required API endpoints exist for the target flow.
4. Frontend API and WebSocket URLs point to the running backend.
5. Next.js static asset handling is compatible with Cesium.

## End-to-End Flow To Validate

1. Backend server starts.
2. Frontend server starts.
3. Frontend loads without fatal Cesium or asset errors.
4. WebSocket connects on page load.
5. Manual simulation trigger works from the real UI.
6. Backend processes the signal and updates state.
7. WebSocket broadcasts the new state or agent payload.
8. Frontend store receives the update.
9. HUD, panels, and map reflect the change.

## Failure Isolation Order

1. Boot and import failures
2. Missing or broken endpoint handlers
3. Backend orchestration and state update failures
4. WebSocket connection or broadcast failures
5. Frontend store or parsing failures
6. Cesium rendering or UI presentation failures

## Quality Criteria

- Backend and frontend use the same payload shapes.
- Manual signal injection exercises the real integration path.
- Reconnection logic is preserved when the backend restarts.
- Verification includes both command success and visible behavior.
- Any remaining limitation is stated as prototype-only, mocked, or unverified.