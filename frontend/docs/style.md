# FRONTEND VIBE & SKILL DIRECTIVE: "LOGOSGATHAM WORLDVIEW"

## 1. Aesthetic & UI Philosophy
You are building a military-grade, Palantir-inspired logistics intelligence dashboard. 
Target Vibe: Top Secret Command Center, Cybernetic, CRT Monitor, Tactical HUD.
Reference: "WORLDVIEW" / SI-TK / NOFORN styling.

## 2. Color Palette & Typography
- **Backgrounds:** Deep void blacks (`#050505`) and dark gunmetal (`#0A0A0A`).
- **Primary Accents:** Tactical Cyan/Teal (`#00F0FF`), Radar Green (`#00FF41`).
- **Alert Colors:** Hazard Amber (`#FFB000`), Critical Red (`#FF003C`).
- **Typography:** MUST use monospace fonts for all telemetry, labels, and coordinates (e.g., `Space Mono`, `JetBrains Mono`, or `Fira Code`). Use a clean sans-serif (e.g., `Inter` or `Geist`) only for long-form reading. All UI headers should be UPPERCASE with wide letter-spacing.

## 3. CSS & Visual Effects (CRITICAL)
- **CRT Effect:** Implement a subtle CSS overlay with scanlines (`repeating-linear-gradient`), a slight vignette, and a very faint chromatic aberration (text-shadow: 1px 0 0 red, -1px 0 0 blue) on headers.
- **The Lens:** The center map should feel like a circular or heavily chamfered viewport/lens, surrounded by dark UI panels.
- **Borders:** UI panels should not have soft shadows. Use hard 1px solid borders (`border-cyan-900/30`) with sharp or chamfered corners.
- **Animations:** Minimal and precise. Blinking recording dots (🔴 REC), typing-effect text reveals, and sharp snap-to-grid panel expansions.

## 4. Layout Structure
- **Left Panel (Data Layers):** Toggles for "Live Shipments", "Weather Radar", "Port Congestion", "Road Closures".
- **Center (The Globe):** Full-screen CesiumJS container.
- **Right/Bottom Panel (Agent HUD):** A telemetry readout showing the LangGraph AI Agents' "Thought Process" and the "Approve/Reject" action buttons.

## 5. Tech Stack Enforcement
- React (Next.js App Router).
- TailwindCSS for all styling (use arbitrary values like `bg-[#050505]` heavily).
- Zustand for global state (Shipments, Disruptions, Active Alerts).
- CesiumJS for the 3D map (do not use Leaflet or Mapbox for the final build, we need 3D volumes).