# Implementation Plan: LogosGotham Intelligence Platform

## Overview

This implementation plan breaks down the LogosGotham Intelligence Platform into discrete coding tasks. The platform consists of a Python backend (FastAPI, NetworkX, Shapely, LangGraph) and a TypeScript frontend (Next.js, React, CesiumJS). The implementation follows a layered approach, building from data models and core infrastructure up through the intelligence layers to the user interface.

## Tasks

- [ ] 1. Set up project structure and core data models
  - Create backend directory structure (api, models, services, agents)
  - Create frontend directory structure (components, pages, hooks, services)
  - Set up Python virtual environment and install dependencies (FastAPI, NetworkX, Shapely, LangGraph, Pydantic, Groq SDK)
  - Set up Next.js project with TypeScript and install dependencies (CesiumJS, TailwindCSS, React Query)
  - Configure environment variables for API keys (Groq, NewsAPI, Open-Meteo, MapmyIndia)
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 3.1, 3.2, 3.3_

- [ ] 2. Implement core data models and schemas
  - [ ] 2.1 Create Pydantic models for all data schemas
    - Implement Coordinates model with lat/lon validation
    - Implement DisruptionObject model with polygon validation and closed polygon check
    - Implement Shipment model with status and location tracking
    - Implement Route, Waypoint, and RoadSegment models
    - Implement RerouteOption and CostMetrics models
    - Implement Recommendation and RiskAssessment models
    - Implement User and UserPermissions models
    - Implement IntersectionEvent model
    - _Requirements: 3.1, 3.2, 3.3, 13.1, 13.2, 13.3, 13.4, 13.5_


  - [ ]* 2.2 Write property test for DisruptionObject schema
    - **Property 1: Round-trip consistency for DisruptionObject**
    - **Validates: Requirements 13.8**
    - Test that parsing then serializing then parsing produces equivalent object

  - [ ]* 2.3 Write unit tests for data model validation
    - Test polygon validation (minimum 3 points, closed polygon)
    - Test coordinate bounds validation (-90 to 90 lat, -180 to 180 lon)
    - Test enum validation (severity, type, status)
    - Test timestamp validation (end_time after start_time)
    - _Requirements: 13.2, 13.3, 13.4, 13.5, 13.6_

- [ ] 3. Implement Ontology Engine with NetworkX graph database
  - [ ] 3.1 Create GraphDatabase class with NetworkX
    - Initialize NetworkX directed graph
    - Implement node creation methods (add_node with attributes)
    - Implement node update methods (update node attributes)
    - Implement node deletion methods (remove_node)
    - Implement edge creation methods (add_edge between nodes)
    - Implement query methods (get nodes by attribute filters)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.9, 3.10_

  - [ ] 3.2 Implement ShipmentManager service
    - Implement create_shipment method with validation
    - Implement update_shipment_location method
    - Implement update_shipment_route method
    - Implement update_shipment_status method
    - Implement get_active_shipments query
    - Implement query_shipments_by_status method
    - _Requirements: 3.1, 3.4, 3.5, 8.4, 8.5, 8.6, 8.7_


  - [ ] 3.3 Implement DisruptionManager service
    - Implement add_disruption method
    - Implement remove_disruption method (triggered by end_time)
    - Implement get_active_disruptions query
    - Implement query_disruptions_by_severity method
    - Implement archive_disruption method for historical storage
    - _Requirements: 3.3, 3.6, 3.7, 3.10, 16.1, 16.2_

  - [ ] 3.4 Implement RouteManager service
    - Implement calculate_route method using MapmyIndia API
    - Implement validate_route method (waypoint count, geographic bounds, road connectivity)
    - Implement route storage and retrieval
    - _Requirements: 3.2, 8.3, 17.1, 17.2, 17.3, 17.4, 17.5_

  - [ ]* 3.5 Write unit tests for Ontology Engine
    - Test shipment CRUD operations with timing constraints (< 100ms)
    - Test disruption CRUD operations with timing constraints (< 100ms)
    - Test query performance (< 50ms for active entities)
    - Test edge creation between shipments and routes
    - _Requirements: 3.4, 3.5, 3.6, 3.9, 3.10_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Signal Ingestion Layer
  - [ ] 5.1 Create DataAggregator with multi-source polling
    - Implement poll_weather_api method for Open-Meteo integration
    - Implement poll_news_api method for NewsAPI integration
    - Implement poll_infrastructure_api method for MapmyIndia integration
    - Implement async polling loop with 5-minute intervals
    - Implement retry logic with exponential backoff (3 attempts)
    - Implement timeout handling (10 seconds per API call)
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 15.4_


  - [ ] 5.2 Create SignalQueue for buffering
    - Implement in-memory queue with enqueue/dequeue operations
    - Implement forward_to_processor method with 1-second latency requirement
    - Implement queue size monitoring
    - _Requirements: 1.6_

  - [ ] 5.3 Create SourceMonitor for availability tracking
    - Implement get_source_status method returning availability dict
    - Implement failure logging when sources become unavailable
    - Implement graceful degradation (continue with available sources)
    - _Requirements: 1.4, 15.4_

  - [ ]* 5.4 Write unit tests for Signal Ingestion Layer
    - Test polling interval accuracy
    - Test retry logic and exponential backoff
    - Test timeout handling
    - Test graceful degradation when sources fail
    - _Requirements: 1.4, 1.5, 15.4_

- [ ] 6. Implement RAG Signal Processor
  - [ ] 6.1 Create GroqAPIClient with retry logic
    - Implement API call wrapper with Groq SDK
    - Implement retry logic (3 attempts with exponential backoff)
    - Implement error handling and logging
    - _Requirements: 2.1, 15.1, 15.2_

  - [ ] 6.2 Create EntityExtractor with LLM prompting
    - Implement extract_entities method with structured prompt template
    - Parse LLM response JSON for location, start_time, duration, type, severity
    - Implement validation of extracted entities
    - _Requirements: 2.1, 2.2, 2.3, 2.4_


  - [ ] 6.3 Create GeocodingService with MapmyIndia integration
    - Implement geocode_location method to convert location names to coordinates
    - Implement error handling for failed geocoding
    - Implement caching for frequently geocoded locations
    - _Requirements: 2.5, 2.6_

  - [ ] 6.4 Create SchemaFormatter for DisruptionObject construction
    - Implement format_disruption_object method
    - Create polygon from geocoded coordinates (buffer around point or bounding box)
    - Validate DisruptionObject schema before returning
    - _Requirements: 2.5_

  - [ ] 6.5 Implement RAGSignalProcessor orchestration
    - Implement process_signal method coordinating all sub-components
    - Enforce 3-second processing time budget
    - Implement signal discarding when geocoding fails
    - _Requirements: 2.6, 2.7_

  - [ ]* 6.6 Write unit tests for RAG Signal Processor
    - Test entity extraction with sample news text
    - Test geocoding with known locations
    - Test DisruptionObject formatting
    - Test processing time constraint (< 3 seconds)
    - Test error handling for failed geocoding
    - _Requirements: 2.6, 2.7, 15.1, 15.2_

- [ ] 7. Implement Geospatial Reasoning Engine
  - [ ] 7.1 Create LookaheadCalculator for route segment generation
    - Implement calculate_lookahead_segment method
    - Extract next 15km of waypoints from current shipment position
    - Convert waypoints to Shapely LineString
    - _Requirements: 4.1_


  - [ ] 7.2 Create IntersectionDetector with Shapely
    - Implement detect_intersections method using Shapely intersects()
    - Check lookahead segment against all active disruption polygons
    - Create IntersectionEvent objects for detected intersections
    - _Requirements: 4.3, 4.4_

  - [ ] 7.3 Create DistanceCalculator
    - Implement calculate_distance_to_hazard using Shapely distance()
    - Calculate distance from current position to hazard polygon boundary
    - _Requirements: 4.4_

  - [ ] 7.4 Implement GeospatialReasoningEngine orchestration
    - Implement intersection checking triggered by shipment location updates
    - Implement intersection checking triggered by new disruptions
    - Implement severity-based prioritization (critical first)
    - Enforce 500ms performance constraint per shipment
    - Enforce 2-second batch processing for 1000 shipments
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 18.1, 20.1, 20.3_

  - [ ]* 7.5 Write unit tests for Geospatial Reasoning Engine
    - Test lookahead segment calculation with sample routes
    - Test intersection detection with overlapping polygons
    - Test distance calculation accuracy
    - Test performance constraints (< 500ms per shipment)
    - Test severity-based prioritization
    - _Requirements: 4.5, 4.6, 18.1_


- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement Agentic Reasoning Engine with LangGraph
  - [ ] 9.1 Define LangGraph state machine schema
    - Create AgentState TypedDict with all required fields
    - Define state transitions between agents
    - _Requirements: 5.1, 5.2, 5.7_

  - [ ] 9.2 Implement RiskAnalyst agent
    - Implement assess_risk method analyzing disruption impact
    - Calculate time_to_impact_minutes from current position to hazard
    - Calculate urgency_score based on severity and time to impact
    - Determine severity_level and affected_shipment_count
    - Return RiskAssessment object
    - _Requirements: 5.1_

  - [ ] 9.3 Implement RouteOptimizer agent
    - Implement generate_alternatives method querying MapmyIndia API
    - Generate minimum 2 alternative routes avoiding hazard zones
    - Implement calculate_cost_metrics for each alternative
    - Calculate additional_distance_km and additional_time_minutes
    - Calculate fuel_cost_inr at 8 INR/km rate
    - Calculate overtime_cost_inr when additional time > 2 hours
    - Round all costs to 2 decimal places
    - Return list of RerouteOption objects
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_


  - [ ] 9.4 Implement ActionComposer agent
    - Implement compose_recommendation method
    - Generate human-readable explanation of disruption and reasoning
    - Format cost-benefit analysis for each reroute option
    - Suggest best option or delay recommendation when no feasible routes exist
    - Return Recommendation object with reasoning text
    - _Requirements: 5.7, 5.8, 5.10_

  - [ ] 9.5 Implement AgenticReasoningEngine orchestration
    - Implement process_intersection_event method with LangGraph state machine
    - Chain agents: RiskAnalyst → RouteOptimizer → ActionComposer
    - Enforce 5-second workflow time constraint
    - Implement parallel processing for multiple affected shipments
    - _Requirements: 5.1, 5.2, 5.7, 5.9, 18.4_

  - [ ]* 9.6 Write unit tests for Agentic Reasoning Engine
    - Test RiskAnalyst urgency score calculation
    - Test RouteOptimizer cost calculations
    - Test ActionComposer recommendation formatting
    - Test full workflow timing (< 5 seconds)
    - Test fallback to delay recommendation when no routes exist
    - _Requirements: 5.9, 5.10, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [ ] 10. Implement GPS simulation for prototype mode
  - [ ] 10.1 Create GPSSimulator service
    - Implement generate_simulated_coordinates method
    - Advance position along route at 50 km/h simulated speed
    - Update coordinates every 30 seconds
    - Add random variance up to 50 meters for GPS accuracy simulation
    - _Requirements: 9.1, 9.2, 9.3, 9.5_


  - [ ] 10.2 Integrate GPS simulation with ShipmentManager
    - Implement simulation mode toggle
    - Update shipment location using simulated coordinates
    - Handle reroute updates to simulation path
    - _Requirements: 9.4_

  - [ ]* 10.3 Write unit tests for GPS simulation
    - Test coordinate generation along route
    - Test speed accuracy (50 km/h)
    - Test update interval (30 seconds)
    - Test position variance (up to 50 meters)
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

- [ ] 11. Implement Backend API with FastAPI
  - [ ] 11.1 Create FastAPI application structure
    - Initialize FastAPI app with CORS middleware
    - Set up route handlers for all endpoints
    - Configure async/await support
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [ ] 11.2 Implement authentication endpoints
    - Implement POST /api/auth/login with JWT token generation
    - Implement POST /api/auth/logout with token invalidation
    - Implement GET /api/auth/me for current user info
    - Implement JWT verification middleware
    - Implement 8-hour session timeout
    - _Requirements: 11.1, 11.2, 11.7_

  - [ ] 11.3 Implement authorization middleware
    - Implement role-based access control (RBAC)
    - Create authorize_action method checking user permissions
    - Implement UserPermissions.from_role factory method
    - Log unauthorized access attempts
    - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6_


  - [ ] 11.4 Implement shipment endpoints
    - Implement POST /api/shipments/create with validation
    - Implement GET /api/shipments/{shipment_id}
    - Implement GET /api/shipments/active
    - Implement PATCH /api/shipments/{shipment_id}/location
    - Implement PATCH /api/shipments/{shipment_id}/status
    - Apply role-based filtering (Seller sees own, Receiver sees incoming, Admin sees all)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.3, 11.4, 11.5_

  - [ ] 11.5 Implement disruption endpoints
    - Implement GET /api/disruptions/active
    - Implement GET /api/disruptions/historical with date range query
    - _Requirements: 16.3, 16.4_

  - [ ] 11.6 Implement reroute endpoints
    - Implement POST /api/reroutes/{recommendation_id}/approve
    - Implement POST /api/reroutes/{recommendation_id}/reject with reason
    - Update Ontology Engine when reroute approved
    - Log rejection reasons
    - _Requirements: 6.7, 6.8_

  - [ ] 11.7 Implement report generation endpoint
    - Implement POST /api/reports/generate with date range
    - Generate PDF with shipment statistics (total, in_transit, delivered)
    - Include disruption statistics (count by type and severity)
    - Include reroute statistics (total, approved, rejected)
    - Calculate cost savings from approved reroutes
    - Complete generation within 5 seconds
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7_


  - [ ]* 11.8 Write unit tests for Backend API
    - Test authentication flow and JWT generation
    - Test authorization for different roles
    - Test shipment CRUD operations
    - Test role-based filtering
    - Test report generation
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 19.7_

- [ ] 12. Implement WebSocket server for real-time updates
  - [ ] 12.1 Create WebSocketManager
    - Implement handle_websocket_connection for client connections
    - Implement connection tracking by user_id
    - Implement channel subscription (shipments, disruptions, recommendations)
    - Support up to 50 concurrent connections
    - _Requirements: 12.1, 20.4_

  - [ ] 12.2 Implement broadcast methods
    - Implement broadcast_shipment_update with 500ms latency requirement
    - Implement broadcast_disruption_alert with 500ms latency requirement
    - Implement send_recommendation to specific Admin users with 500ms latency
    - Filter broadcasts based on user role and permissions
    - _Requirements: 12.2, 12.3, 12.4_

  - [ ] 12.3 Implement connection resilience
    - Implement heartbeat/ping mechanism
    - Handle connection drops gracefully
    - Implement state sync on reconnection
    - _Requirements: 12.5, 12.6_

  - [ ]* 12.4 Write unit tests for WebSocket server
    - Test connection handling
    - Test broadcast latency (< 500ms)
    - Test role-based filtering
    - Test reconnection and state sync
    - _Requirements: 12.2, 12.3, 12.4, 12.6_


- [ ] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement frontend Next.js application structure
  - [ ] 14.1 Create Next.js project with TypeScript
    - Initialize Next.js 14 project with App Router
    - Configure TypeScript with strict mode
    - Install dependencies (CesiumJS, TailwindCSS, React Query, WebSocket client)
    - Set up TailwindCSS configuration
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ] 14.2 Create TypeScript interfaces for data models
    - Define interfaces matching backend Pydantic models
    - Create Coordinates, DisruptionObject, Shipment, Route interfaces
    - Create RerouteOption, Recommendation, User interfaces
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 14.3 Set up authentication context and hooks
    - Create AuthContext with user state and login/logout methods
    - Create useAuth hook for accessing auth state
    - Implement protected route wrapper component
    - Store JWT token in localStorage with 8-hour expiry
    - _Requirements: 11.1, 11.2, 11.7_

  - [ ] 14.4 Set up WebSocket context and hooks
    - Create WebSocketContext with connection management
    - Implement useWebSocket hook for subscribing to channels
    - Implement automatic reconnection every 5 seconds on disconnect
    - Implement connection status indicator
    - _Requirements: 12.1, 12.5, 15.5_


  - [ ] 14.5 Set up React Query for server state management
    - Configure QueryClient with default options
    - Create query hooks for shipments, disruptions, recommendations
    - Implement optimistic updates for mutations
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 15. Implement CesiumJS 3D globe visualization
  - [ ] 15.1 Create CesiumGlobe component
    - Initialize Cesium Viewer with WebGL rendering
    - Configure camera controls (pan, zoom, rotate)
    - Set up terrain and imagery providers
    - Implement smooth camera animations
    - Optimize for 30+ FPS with up to 1000 entities
    - Load initial view within 3 seconds
    - _Requirements: 7.1, 7.8, 7.9, 20.2, 20.5_

  - [ ] 15.2 Create ShipmentMarker component
    - Render 3D markers at shipment coordinates
    - Implement click handler to show shipment details popup
    - Update marker position in real-time via WebSocket
    - Implement marker clustering for performance with many shipments
    - _Requirements: 7.2, 7.5, 7.7_

  - [ ] 15.3 Create RoutePolyline component
    - Render routes as 3D polylines on Earth surface
    - Color-code routes by status (active, rerouted, completed)
    - Implement hover effects
    - _Requirements: 7.3_


  - [ ] 15.4 Create HazardZone component
    - Render disruption polygons as semi-transparent 3D shapes
    - Implement color coding by severity (yellow=low, orange=medium, red=high, purple=critical)
    - Implement pulsing animation for critical severity
    - Implement click handler to show disruption details popup
    - _Requirements: 7.4, 7.6, 18.3_

  - [ ] 15.5 Integrate real-time updates with CesiumGlobe
    - Subscribe to WebSocket shipment updates
    - Update marker positions with 10-second maximum interval
    - Subscribe to WebSocket disruption alerts
    - Add/remove hazard zones dynamically
    - _Requirements: 7.7, 12.2, 12.3_

  - [ ]* 15.6 Write unit tests for Cesium components
    - Test marker rendering and positioning
    - Test polyline rendering
    - Test hazard zone color coding
    - Test click handlers
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 16. Implement Admin dashboard and recommendation panel
  - [ ] 16.1 Create AdminDashboard page component
    - Layout with CesiumGlobe and side panels
    - Display active shipments count
    - Display active disruptions count
    - Display pending recommendations count
    - Implement filter controls (show only critical, by type, by status)
    - _Requirements: 6.1, 11.3, 18.5_


  - [ ] 16.2 Create RecommendationPanel component
    - Display pending reroute recommendations with priority sorting
    - Show original route vs alternative routes on globe
    - Display hazard zone polygon
    - Display cost comparison table (distance, time, fuel, overtime, total)
    - Display AI reasoning explanation from ActionComposer
    - Implement route selection highlighting
    - Implement Approve button with option selection
    - Implement Reject button with reason input
    - Show notification within 1 second of recommendation generation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 18.2_

  - [ ] 16.3 Implement reroute approval flow
    - Call POST /api/reroutes/{id}/approve on approval
    - Update Ontology Engine and trigger WebSocket broadcast
    - Update globe visualization with new route within 500ms
    - _Requirements: 6.7_

  - [ ] 16.4 Implement reroute rejection flow
    - Call POST /api/reroutes/{id}/reject with reason
    - Dismiss recommendation from panel
    - Log rejection for analytics
    - _Requirements: 6.8_

  - [ ]* 16.5 Write unit tests for Admin dashboard
    - Test recommendation display and sorting
    - Test cost comparison rendering
    - Test approval/rejection flows
    - Test notification timing (< 1 second)
    - _Requirements: 6.1, 6.7, 6.8_


- [ ] 17. Implement Seller shipment creation interface
  - [ ] 17.1 Create ShipmentCreationForm component
    - Implement origin input with geocoding autocomplete
    - Implement destination input with geocoding autocomplete
    - Implement cargo details input (weight, type, value)
    - Implement route preview on globe before submission
    - Validate origin and destination coordinates
    - _Requirements: 8.1, 8.2_

  - [ ] 17.2 Integrate form with backend API
    - Call POST /api/shipments/create on form submission
    - Handle validation errors from backend (invalid coordinates, route validation failures)
    - Display success message and redirect to tracking view
    - _Requirements: 8.2, 8.3, 8.4, 17.4, 17.5_

  - [ ] 17.3 Create SellerDashboard page component
    - Display shipments created by current Seller user
    - Show shipment status and current location
    - Show ETA with automatic updates
    - Provide access to ShipmentCreationForm
    - _Requirements: 11.4_

  - [ ]* 17.4 Write unit tests for Seller interface
    - Test form validation
    - Test geocoding integration
    - Test shipment creation flow
    - Test error handling
    - _Requirements: 8.1, 8.2, 8.3, 17.4_


- [ ] 18. Implement Receiver dashboard
  - [ ] 18.1 Create ReceiverDashboard page component
    - Display read-only view of incoming shipments (where user is receiver)
    - Show current shipment location on globe
    - Show current ETA with automatic updates when routes change
    - Show shipment status (pending, in_transit, delivered)
    - Update ETA within 2 seconds of reroute
    - Prevent access to Admin controls and other shipments
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.5_

  - [ ]* 18.2 Write unit tests for Receiver dashboard
    - Test shipment filtering (only incoming shipments)
    - Test ETA display and updates
    - Test access control (no Admin features)
    - _Requirements: 10.2, 10.6, 10.7, 11.5_

- [ ] 19. Implement historical data and reporting features
  - [ ] 19.1 Create HistoricalView component for Admin
    - Implement date range selector
    - Display disruptions that occurred during selected period
    - Display statistics on disruption frequency by type and severity
    - Visualize historical disruptions on globe
    - _Requirements: 16.3, 16.4, 16.5_

  - [ ] 19.2 Create ReportGenerator component
    - Implement date range selector for report scope
    - Call POST /api/reports/generate endpoint
    - Download generated PDF report
    - Display loading state during generation (< 5 seconds)
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7_


  - [ ]* 19.3 Write unit tests for historical and reporting features
    - Test date range filtering
    - Test statistics calculation
    - Test report generation
    - _Requirements: 16.4, 16.5, 19.7_

- [ ] 20. Implement simulation mode indicator and controls
  - [ ] 20.1 Create SimulationModeIndicator component
    - Display "SIMULATION MODE" banner when prototype mode is active
    - Show current simulation speed and update interval
    - _Requirements: 9.6_

  - [ ] 20.2 Create SimulationControls component for Admin
    - Implement toggle to enable/disable simulation mode
    - Implement speed adjustment controls (10x, 50x, 100x)
    - Implement manual position advancement for testing
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 21. Implement error handling and logging
  - [ ] 21.1 Create centralized error logging service
    - Log all API failures with timestamp, endpoint, error details
    - Log authentication failures and unauthorized access attempts
    - Log signal processing failures
    - _Requirements: 15.6, 11.6_

  - [ ] 21.2 Implement user-facing error messages
    - Display connection status indicator for WebSocket
    - Display error toasts for failed operations
    - Provide retry buttons for recoverable errors
    - _Requirements: 15.5_

