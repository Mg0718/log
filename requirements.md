# Requirements Document

## Introduction

LogosGotham is a proactive logistics intelligence system for the Indian logistics network that shifts from reactive tracking to proactive disruption prediction. The system ingests real-time environmental signals (news, weather, infrastructure alerts), translates them into structured geospatial hazard zones, maintains a live digital twin of active shipments and routes, and uses autonomous AI agents to calculate spatial intersections and generate actionable rerouting recommendations with cost evaluations for human approval.

## Glossary

- **Signal_Ingestion_Layer**: The subsystem that aggregates multi-source environmental data feeds
- **RAG_Signal_Processor**: The subsystem that uses LLMs to extract entities from unstructured text and format them into structured schemas
- **Ontology_Engine**: The in-memory graph database that maintains the digital twin of shipments, routes, and disruptions
- **Geospatial_Reasoning_Engine**: The subsystem that performs spatial intersection calculations between routes and hazard zones
- **Agentic_Reasoning_Engine**: The LangGraph state machine with three specialized AI agents
- **Intelligence_Map**: The 3D visualization interface for monitoring operations
- **DisruptionObject**: A structured schema representing a geospatial hazard with polygon boundaries and metadata
- **Shipment**: A logistics entity with origin, destination, current location, and route information
- **Route**: A geographic path defined by waypoints and road segments
- **Hazard_Zone**: A 3D polygon representing a geographic area affected by a disruption
- **Lookahead_Distance**: The 15km forward distance along a route used for intersection detection
- **Reroute_Option**: An alternative route with calculated cost and time impact
- **Admin**: A dispatcher user who monitors operations and approves reroutes
- **Seller**: An originator user who creates and dispatches shipments
- **Receiver**: A destination user with read-only access to shipment status
- **TMS**: Transportation Management System (external system, not part of LogosGotham)

## Requirements

### Requirement 1: Ingest Environmental Signals

**User Story:** As an Admin, I want the system to continuously ingest real-time environmental data from multiple sources, so that I have current information about potential logistics disruptions.

#### Acceptance Criteria

1. THE Signal_Ingestion_Layer SHALL aggregate data from Open-Meteo weather API
2. THE Signal_Ingestion_Layer SHALL aggregate data from NewsAPI for news feeds
3. THE Signal_Ingestion_Layer SHALL aggregate data from MapmyIndia for infrastructure alerts
4. WHEN a data source becomes unavailable, THE Signal_Ingestion_Layer SHALL log the failure and continue ingesting from available sources
5. THE Signal_Ingestion_Layer SHALL poll each data source at intervals not exceeding 5 minutes
6. WHEN new signal data is received, THE Signal_Ingestion_Layer SHALL forward it to the RAG_Signal_Processor within 1 second

### Requirement 2: Extract Structured Disruption Data

**User Story:** As an Admin, I want unstructured text signals to be automatically converted into structured geospatial data, so that the system can reason about disruptions spatially.

#### Acceptance Criteria

1. WHEN the RAG_Signal_Processor receives unstructured text, THE RAG_Signal_Processor SHALL extract location entities using Groq API with Llama 3
2. WHEN the RAG_Signal_Processor receives unstructured text, THE RAG_Signal_Processor SHALL extract temporal information (start time, duration)
3. WHEN the RAG_Signal_Processor receives unstructured text, THE RAG_Signal_Processor SHALL extract disruption type (weather, infrastructure, traffic, protest)
4. WHEN the RAG_Signal_Processor receives unstructured text, THE RAG_Signal_Processor SHALL extract severity level (low, medium, high, critical)
5. THE RAG_Signal_Processor SHALL format extracted data into a DisruptionObject schema with geospatial polygon coordinates
6. WHEN location entities cannot be geocoded, THE RAG_Signal_Processor SHALL log the failure and discard the signal
7. THE RAG_Signal_Processor SHALL complete processing within 3 seconds per signal

### Requirement 3: Maintain Ontology Graph

**User Story:** As an Admin, I want the system to maintain a live digital twin of all shipments, routes, and disruptions, so that I have an accurate real-time view of the logistics network.

#### Acceptance Criteria

1. THE Ontology_Engine SHALL store shipment nodes with attributes (id, origin, destination, current_location, status, dispatch_time)
2. THE Ontology_Engine SHALL store route nodes with attributes (id, waypoints, road_segments, estimated_duration)
3. THE Ontology_Engine SHALL store disruption nodes with attributes (id, polygon, type, severity, start_time, end_time)
4. WHEN a new shipment is created, THE Ontology_Engine SHALL add the shipment node within 100 milliseconds
5. WHEN a shipment location is updated, THE Ontology_Engine SHALL update the current_location attribute within 100 milliseconds
6. WHEN a new DisruptionObject is received, THE Ontology_Engine SHALL add the disruption node within 100 milliseconds
7. WHEN a disruption end_time is reached, THE Ontology_Engine SHALL remove the disruption node within 1 second
8. THE Ontology_Engine SHALL maintain edges between shipments and their assigned routes
9. THE Ontology_Engine SHALL support queries for all active shipments within 50 milliseconds
10. THE Ontology_Engine SHALL support queries for all active disruptions within 50 milliseconds

### Requirement 4: Calculate Route-Hazard Intersections

**User Story:** As an Admin, I want the system to automatically detect when shipment routes intersect with hazard zones, so that I can proactively address potential disruptions.

#### Acceptance Criteria

1. WHEN a shipment location is updated, THE Geospatial_Reasoning_Engine SHALL calculate the Lookahead_Distance segment (15km forward along the route)
2. WHEN a new disruption is added, THE Geospatial_Reasoning_Engine SHALL check all active shipment lookahead segments for intersections
3. THE Geospatial_Reasoning_Engine SHALL use Shapely library for polygon intersection calculations
4. WHEN a lookahead segment intersects a Hazard_Zone, THE Geospatial_Reasoning_Engine SHALL create an intersection event with distance-to-hazard and severity
5. THE Geospatial_Reasoning_Engine SHALL complete intersection calculations within 500 milliseconds per shipment
6. THE Geospatial_Reasoning_Engine SHALL prioritize intersection checks by disruption severity (critical first)

### Requirement 5: Generate Reroute Recommendations

**User Story:** As an Admin, I want the system to automatically generate alternative route options with cost analysis when disruptions are detected, so that I can make informed rerouting decisions.

#### Acceptance Criteria

1. WHEN an intersection event is created, THE Agentic_Reasoning_Engine SHALL invoke the RiskAnalyst agent to assess disruption impact
2. WHEN the RiskAnalyst agent completes assessment, THE Agentic_Reasoning_Engine SHALL invoke the RouteOptimizer agent to generate alternative routes
3. THE RouteOptimizer agent SHALL generate at least 2 alternative Reroute_Options when feasible routes exist
4. THE RouteOptimizer agent SHALL calculate additional distance for each Reroute_Option
5. THE RouteOptimizer agent SHALL calculate additional time for each Reroute_Option
6. THE RouteOptimizer agent SHALL calculate additional fuel cost for each Reroute_Option
7. WHEN the RouteOptimizer agent completes, THE Agentic_Reasoning_Engine SHALL invoke the ActionComposer agent to format recommendations
8. THE ActionComposer agent SHALL generate a human-readable explanation of the disruption and recommended actions
9. THE Agentic_Reasoning_Engine SHALL complete the full agent workflow within 5 seconds per intersection event
10. WHEN no feasible alternative routes exist, THE ActionComposer agent SHALL recommend delaying the shipment with estimated wait time

### Requirement 6: Provide Admin Approval Interface

**User Story:** As an Admin, I want to review AI-generated reroute recommendations and approve or reject them, so that I maintain control over logistics decisions.

#### Acceptance Criteria

1. WHEN a reroute recommendation is generated, THE Intelligence_Map SHALL display a notification to the Admin within 1 second
2. THE Intelligence_Map SHALL display the original route and all Reroute_Options on the 3D globe
3. THE Intelligence_Map SHALL display the Hazard_Zone polygon on the 3D globe
4. THE Intelligence_Map SHALL display cost comparison data (distance, time, fuel) for each Reroute_Option
5. THE Intelligence_Map SHALL display the AI reasoning explanation from the ActionComposer agent
6. WHEN the Admin selects a Reroute_Option, THE Intelligence_Map SHALL highlight the selected route
7. WHEN the Admin approves a reroute, THE Ontology_Engine SHALL update the shipment route within 500 milliseconds
8. WHEN the Admin rejects a reroute, THE Intelligence_Map SHALL dismiss the recommendation and log the rejection reason

### Requirement 7: Render 3D Intelligence Map

**User Story:** As an Admin, I want to visualize all shipments, routes, and disruptions on a photorealistic 3D globe, so that I can understand the spatial context of operations.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL render a 3D Earth using CesiumJS with WebGL
2. THE Intelligence_Map SHALL display active shipment locations as 3D markers with real-time position updates
3. THE Intelligence_Map SHALL display routes as 3D polylines on the Earth surface
4. THE Intelligence_Map SHALL display Hazard_Zone polygons as semi-transparent 3D shapes with color-coded severity (yellow=low, orange=medium, red=high, purple=critical)
5. WHEN a shipment marker is clicked, THE Intelligence_Map SHALL display a popup with shipment details (id, origin, destination, status, ETA)
6. WHEN a Hazard_Zone is clicked, THE Intelligence_Map SHALL display a popup with disruption details (type, severity, start_time, end_time)
7. THE Intelligence_Map SHALL update shipment positions at intervals not exceeding 10 seconds
8. THE Intelligence_Map SHALL support camera controls (pan, zoom, rotate) with smooth animations
9. THE Intelligence_Map SHALL load initial view within 3 seconds on standard broadband connections

### Requirement 8: Manage Shipment Lifecycle

**User Story:** As a Seller, I want to create and dispatch shipments with origin, destination, and cargo details, so that the system can track and protect my logistics operations.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL provide a shipment creation form for Seller users
2. WHEN a Seller submits a shipment form, THE Ontology_Engine SHALL validate that origin and destination are valid geographic coordinates
3. WHEN a Seller submits a shipment form, THE Ontology_Engine SHALL calculate an initial route using MapmyIndia routing API
4. WHEN a Seller submits a shipment form, THE Ontology_Engine SHALL create a shipment node with status "pending"
5. WHEN a Seller dispatches a shipment, THE Ontology_Engine SHALL update status to "in_transit" and record dispatch_time
6. WHEN a shipment reaches its destination, THE Ontology_Engine SHALL update status to "delivered" and record delivery_time
7. THE Ontology_Engine SHALL assign a unique identifier to each shipment
8. THE Ontology_Engine SHALL calculate initial ETA based on route distance and average speed of 50 km/h

### Requirement 9: Simulate GPS Tracking

**User Story:** As an Admin, I want the system to simulate realistic GPS tracking for prototype demonstration, so that I can showcase the platform without requiring physical IoT hardware.

#### Acceptance Criteria

1. WHERE the system is in prototype mode, THE Ontology_Engine SHALL generate simulated GPS coordinates along the shipment route
2. WHERE the system is in prototype mode, THE Ontology_Engine SHALL update simulated GPS coordinates at intervals of 30 seconds
3. WHERE the system is in prototype mode, THE Ontology_Engine SHALL advance the shipment position along the route at a simulated speed of 50 km/h
4. WHERE the system is in prototype mode, WHEN a reroute is approved, THE Ontology_Engine SHALL update the simulated GPS path to follow the new route
5. WHERE the system is in prototype mode, THE Ontology_Engine SHALL add random position variance of up to 50 meters to simulate GPS accuracy
6. WHERE the system is in prototype mode, THE Intelligence_Map SHALL display a "SIMULATION MODE" indicator

### Requirement 10: Provide Receiver Dashboard

**User Story:** As a Receiver, I want to view the real-time location and ETA of incoming shipments, so that I can prepare for delivery.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL provide a read-only dashboard view for Receiver users
2. THE Intelligence_Map SHALL display only shipments where the Receiver is the destination
3. THE Intelligence_Map SHALL display current shipment location on the 3D globe
4. THE Intelligence_Map SHALL display current ETA with automatic updates when routes change
5. THE Intelligence_Map SHALL display shipment status (pending, in_transit, delivered)
6. WHEN a shipment is rerouted, THE Intelligence_Map SHALL update the ETA within 2 seconds
7. THE Intelligence_Map SHALL prevent Receiver users from accessing Admin controls or other shipments

### Requirement 11: Authenticate and Authorize Users

**User Story:** As a system administrator, I want users to be authenticated and authorized based on their roles, so that access to features is properly controlled.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL require user authentication before granting access
2. WHEN a user authenticates, THE Intelligence_Map SHALL assign role-based permissions (Admin, Seller, or Receiver)
3. THE Intelligence_Map SHALL grant Admin users access to the full 3D globe view, all shipments, and reroute approval controls
4. THE Intelligence_Map SHALL grant Seller users access to shipment creation and their own shipment tracking
5. THE Intelligence_Map SHALL grant Receiver users read-only access to shipments where they are the destination
6. WHEN an unauthorized user attempts to access restricted features, THE Intelligence_Map SHALL deny access and log the attempt
7. THE Intelligence_Map SHALL maintain user sessions for 8 hours of inactivity before requiring re-authentication

### Requirement 12: Provide Real-Time Updates via WebSocket

**User Story:** As an Admin, I want the interface to update in real-time without manual refresh, so that I always see current information.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL establish a WebSocket connection to the backend on page load
2. WHEN a shipment location is updated, THE backend SHALL broadcast the update to all connected Admin clients within 500 milliseconds
3. WHEN a new disruption is added, THE backend SHALL broadcast the disruption to all connected Admin clients within 500 milliseconds
4. WHEN a reroute recommendation is generated, THE backend SHALL send the recommendation to connected Admin clients within 500 milliseconds
5. WHEN the WebSocket connection is lost, THE Intelligence_Map SHALL attempt reconnection every 5 seconds
6. WHEN the WebSocket connection is restored, THE Intelligence_Map SHALL request a full state sync from the backend

### Requirement 13: Parse and Serialize DisruptionObject Schema

**User Story:** As a developer, I want DisruptionObject data to be consistently parsed and serialized, so that data integrity is maintained across system components.

#### Acceptance Criteria

1. THE RAG_Signal_Processor SHALL parse DisruptionObject JSON into Python objects with validated fields
2. THE DisruptionObject_Parser SHALL validate that polygon coordinates form a valid closed polygon
3. THE DisruptionObject_Parser SHALL validate that severity is one of (low, medium, high, critical)
4. THE DisruptionObject_Parser SHALL validate that type is one of (weather, infrastructure, traffic, protest)
5. THE DisruptionObject_Parser SHALL validate that start_time is a valid ISO 8601 timestamp
6. WHEN a DisruptionObject has invalid data, THE DisruptionObject_Parser SHALL return a descriptive error message
7. THE DisruptionObject_Serializer SHALL format DisruptionObject Python objects into valid JSON
8. FOR ALL valid DisruptionObject instances, parsing then serializing then parsing SHALL produce an equivalent object (round-trip property)

### Requirement 14: Calculate Cost Metrics

**User Story:** As an Admin, I want accurate cost calculations for reroute options, so that I can make cost-effective decisions.

#### Acceptance Criteria

1. WHEN the RouteOptimizer agent generates a Reroute_Option, THE RouteOptimizer agent SHALL calculate additional distance in kilometers
2. WHEN the RouteOptimizer agent generates a Reroute_Option, THE RouteOptimizer agent SHALL calculate additional time in minutes
3. WHEN the RouteOptimizer agent generates a Reroute_Option, THE RouteOptimizer agent SHALL calculate fuel cost using a rate of 8 INR per kilometer
4. WHEN the RouteOptimizer agent generates a Reroute_Option, THE RouteOptimizer agent SHALL calculate driver overtime cost when additional time exceeds 2 hours
5. THE RouteOptimizer agent SHALL calculate total additional cost as the sum of fuel cost and overtime cost
6. THE RouteOptimizer agent SHALL round all cost values to 2 decimal places

### Requirement 15: Handle API Failures Gracefully

**User Story:** As an Admin, I want the system to continue operating when external APIs fail, so that temporary outages do not halt operations.

#### Acceptance Criteria

1. WHEN the Groq API returns an error, THE RAG_Signal_Processor SHALL retry the request up to 3 times with exponential backoff
2. WHEN the Groq API fails after retries, THE RAG_Signal_Processor SHALL log the failure and discard the signal
3. WHEN the MapmyIndia routing API returns an error, THE RouteOptimizer agent SHALL use fallback straight-line distance calculations
4. WHEN a data source in the Signal_Ingestion_Layer is unavailable, THE Signal_Ingestion_Layer SHALL continue polling other sources
5. WHEN the WebSocket connection fails, THE Intelligence_Map SHALL display a connection status indicator to users
6. THE backend SHALL log all API failures with timestamp, endpoint, and error details

### Requirement 16: Store Historical Disruption Data

**User Story:** As an Admin, I want to access historical disruption data, so that I can analyze patterns and improve future predictions.

#### Acceptance Criteria

1. WHEN a disruption end_time is reached, THE Ontology_Engine SHALL archive the disruption node to persistent storage
2. THE Ontology_Engine SHALL store archived disruptions with all original attributes and metadata
3. THE Intelligence_Map SHALL provide a historical view mode for Admin users
4. WHEN an Admin selects a date range, THE Intelligence_Map SHALL display all disruptions that occurred during that period
5. THE Intelligence_Map SHALL display statistics on disruption frequency by type and severity
6. THE Ontology_Engine SHALL retain historical data for at least 90 days

### Requirement 17: Validate Route Feasibility

**User Story:** As a Seller, I want the system to validate that my shipment route is feasible, so that I do not dispatch shipments on invalid routes.

#### Acceptance Criteria

1. WHEN a shipment is created, THE Ontology_Engine SHALL validate that the route contains at least 2 waypoints
2. WHEN a shipment is created, THE Ontology_Engine SHALL validate that all waypoints are within the Indian geographic boundary
3. WHEN a shipment is created, THE Ontology_Engine SHALL validate that consecutive waypoints are connected by road segments
4. WHEN route validation fails, THE Ontology_Engine SHALL return an error message indicating the validation failure reason
5. THE Ontology_Engine SHALL prevent shipment creation when route validation fails

### Requirement 18: Prioritize Critical Disruptions

**User Story:** As an Admin, I want critical disruptions to be processed and displayed first, so that I can address the most urgent situations immediately.

#### Acceptance Criteria

1. WHEN multiple disruptions are detected simultaneously, THE Geospatial_Reasoning_Engine SHALL process critical severity disruptions before others
2. WHEN multiple reroute recommendations are pending, THE Intelligence_Map SHALL display critical severity recommendations at the top of the notification list
3. THE Intelligence_Map SHALL use distinct visual styling for critical disruptions (pulsing animation, larger size)
4. WHEN a critical disruption affects multiple shipments, THE Agentic_Reasoning_Engine SHALL generate recommendations for all affected shipments in parallel
5. THE Intelligence_Map SHALL provide a filter to show only critical disruptions

### Requirement 19: Export Operational Reports

**User Story:** As an Admin, I want to export operational reports with shipment and disruption data, so that I can share insights with stakeholders.

#### Acceptance Criteria

1. THE Intelligence_Map SHALL provide a report export feature for Admin users
2. WHEN an Admin requests a report, THE Intelligence_Map SHALL generate a PDF document with shipment statistics (total, in_transit, delivered)
3. WHEN an Admin requests a report, THE Intelligence_Map SHALL include disruption statistics (count by type, count by severity)
4. WHEN an Admin requests a report, THE Intelligence_Map SHALL include reroute statistics (total recommendations, approved, rejected)
5. WHEN an Admin requests a report, THE Intelligence_Map SHALL include cost savings from approved reroutes
6. THE Intelligence_Map SHALL allow Admin users to specify a date range for the report
7. THE Intelligence_Map SHALL generate and download the report within 5 seconds

### Requirement 20: Maintain System Performance Under Load

**User Story:** As an Admin, I want the system to maintain responsive performance even with many active shipments, so that operations scale effectively.

#### Acceptance Criteria

1. WHILE the Ontology_Engine manages up to 1000 active shipments, THE Geospatial_Reasoning_Engine SHALL complete intersection calculations within 2 seconds per update cycle
2. WHILE the Ontology_Engine manages up to 1000 active shipments, THE Intelligence_Map SHALL render all shipment markers within 5 seconds
3. WHILE the Ontology_Engine manages up to 100 active disruptions, THE Geospatial_Reasoning_Engine SHALL complete intersection calculations within 2 seconds per update cycle
4. THE backend SHALL support at least 50 concurrent WebSocket connections
5. THE Intelligence_Map SHALL maintain frame rate above 30 FPS during 3D globe interactions with up to 1000 visible entities

