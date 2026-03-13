"use client";

import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Source/Widgets/widgets.css";
import { useLogisticsStore } from "@/store/useLogisticsStore";

type CesiumWindow = Window & typeof globalThis & {
  CESIUM_BASE_URL?: string;
};

// Cesium needs to know where its assets are
if (typeof window !== "undefined") {
    (window as CesiumWindow).CESIUM_BASE_URL = "/cesium";
    // Set global tokens if available
    if (process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN) {
        Cesium.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;
    }
}

export default function LogosGothamMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const hasInitialFocusRef = useRef(false);
  const { shipments, disruptions, activePayload } = useLogisticsStore();

  const focusOperationalArea = (viewer: Cesium.Viewer, routeOrPoints: [number, number][]) => {
    if (!routeOrPoints.length) {
      viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(78.9629, 20.5937, 3200000),
        orientation: {
          heading: 0,
          pitch: Cesium.Math.toRadians(-32),
          roll: 0,
        },
      });
      return;
    }

    const lons = routeOrPoints.map((point) => point[0]);
    const lats = routeOrPoints.map((point) => point[1]);
    const west = Math.min(...lons);
    const east = Math.max(...lons);
    const south = Math.min(...lats);
    const north = Math.max(...lats);
    const rectangle = Cesium.Rectangle.fromDegrees(west - 2, south - 2, east + 2, north + 2);
    viewer.camera.flyTo({
      destination: rectangle,
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-35),
        roll: 0,
      },
      duration: 1.2,
    });
  };

  const splitRouteByRoadTier = (route: [number, number][]) => {
    if (route.length <= 2) {
      return { major: route, minor: [] as [number, number][] };
    }

    const majorStep = route.length > 50 ? 7 : 4;
    const major: [number, number][] = [];
    const minor: [number, number][] = [];

    route.forEach((coord, idx) => {
      const isEndpoint = idx === 0 || idx === route.length - 1;
      const isMajorWaypoint = idx % majorStep === 0;
      if (isEndpoint || isMajorWaypoint) {
        major.push(coord);
      } else {
        minor.push(coord);
      }
    });

    if (major.length < 2) {
      return { major: route, minor: [] as [number, number][] };
    }
    return { major, minor };
  };

  // 1. Initialize Viewer
  useEffect(() => {
    if (!containerRef.current) return;

    // 2. Initialize the viewer — all stock UI disabled for clean tactical look
    const viewer = new Cesium.Viewer(containerRef.current, {
      timeline: false,
      animation: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      vrButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      scene3DOnly: true,
      shadows: false,
      // Satellite imagery — ESRI World Imagery (free, no API key required)
      baseLayer: new Cesium.ImageryLayer(
        new Cesium.UrlTemplateImageryProvider({
          url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          maximumLevel: 19,
          credit: "Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye",
        })
      ),
    });

    // Hide Cesium logo / attribution bar
    (viewer.cesiumWidget.creditContainer as HTMLElement).style.display = "none";

    // Keep the tactical UI, but let the globe read like a normal Earth.
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#02070d");
    viewer.scene.globe.depthTestAgainstTerrain = true;
    viewer.scene.globe.show = true;
    viewer.scene.globe.enableLighting = false;
    viewer.scene.globe.showGroundAtmosphere = true;
    if (viewer.scene.skyAtmosphere) {
      viewer.scene.skyAtmosphere.show = true;
    }
    if (viewer.scene.skyBox) {
      viewer.scene.skyBox.show = true;
    }

    // Note: Satellite imagery looks best with natural colours and slight darkening.
    const imageryLayer = viewer.imageryLayers.get(0);
    if (imageryLayer) {
        imageryLayer.brightness = 0.85;
        imageryLayer.contrast = 1.05;
        imageryLayer.saturation = 1.0;  // Full colour — satellite view
        imageryLayer.gamma = 0.9;
    }

    // Force a visible Earth viewport on first paint.
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(78.9629, 20.5937, 3200000),
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-32),
        roll: 0,
      },
    });

    viewerRef.current = viewer;

    async function setupTerrain() {
      // 3. Add 3D Terrain (Mountains, valleys) so it's not a flat sphere
      try {
        const terrainProvider = await Cesium.createWorldTerrainAsync();
        if (viewerRef.current && !viewerRef.current.isDestroyed()) {
          viewerRef.current.terrainProvider = terrainProvider;
          if (!hasInitialFocusRef.current) {
            hasInitialFocusRef.current = true;
            focusOperationalArea(viewerRef.current, []);
          }
        }
      } catch (error) {
        console.error("Failed to load 3D terrain:", error);
      }
    }

    setupTerrain();

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
      }
    };
  }, []);

  // 2. Synchronize Shipments & Disruptions (without re-rendering component)
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // Clear existing dynamic entities
    viewer.entities.removeAll();

    const deferredMinorRoads: Array<{ id: string; points: [number, number][]; riskScore: number }> = [];

    // Render Shipments
    shipments.forEach((shp) => {
      // Use real GPS coordinates if present; fall back to first route point
      const truckLon = shp.currentLon ?? shp.currentRoute[0]?.[0];
      const truckLat = shp.currentLat ?? shp.currentRoute[0]?.[1];
      const routePoints = shp.currentRoute as [number, number][];
      const { major, minor } = splitRouteByRoadTier(routePoints);
      viewer.entities.add({
        id: shp.id,
        name: shp.cargo,
        position: Cesium.Cartesian3.fromDegrees(truckLon, truckLat),
        point: {
          pixelSize: 12,
          color: shp.riskScore > 50 ? Cesium.Color.RED : Cesium.Color.fromCssColorString("#00FFFF"),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
        },
        label: {
          text: shp.id,
          font: "10px monospace",
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -15),
          fillColor: Cesium.Color.WHITE,
        },
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(major.flat()),
          width: 6,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.25,
            color: shp.riskScore > 50
              ? Cesium.Color.fromCssColorString("#ff2244")
              : Cesium.Color.fromCssColorString("#00ffcc"),
          }),
        }
      });

      if (minor.length > 1) {
        deferredMinorRoads.push({ id: shp.id, points: minor, riskScore: shp.riskScore });
      }
    });

    if (shipments.length > 0 && !activePayload) {
      const focusPoints = shipments.flatMap((shipment) => {
        const points = shipment.currentRoute?.slice(0, 10) ?? [];
        if (points.length > 0) {
          return points as [number, number][];
        }
        if (shipment.currentLon !== undefined && shipment.currentLat !== undefined) {
          return [[shipment.currentLon, shipment.currentLat] as [number, number]];
        }
        return [];
      });
      if (focusPoints.length > 0) {
        focusOperationalArea(viewer, focusPoints);
      }
    }

    // Defer fine-grained route detail so major corridors appear first.
    const minorRoadTimer = window.setTimeout(() => {
      if (!viewerRef.current || viewerRef.current.isDestroyed()) return;
      deferredMinorRoads.forEach((segment) => {
        viewer.entities.add({
          id: `${segment.id}-minor-road`,
          name: `${segment.id} Secondary Road Detail`,
          polyline: {
            positions: Cesium.Cartesian3.fromDegreesArray(segment.points.flat()),
            width: 2,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.1,
              color: segment.riskScore > 50
                ? Cesium.Color.fromCssColorString("#ff2244").withAlpha(0.45)
                : Cesium.Color.fromCssColorString("#00ffcc").withAlpha(0.35),
            }),
          },
        });
      });
    }, 180);

    // Render Disruption Polygons as 3D Volumes
    disruptions.forEach((evt) => {
        const flatCoords = evt.polygonGeoJSON[0].flat();
        viewer.entities.add({
            id: evt.id,
            name: evt.type,
            polygon: {
                hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                height: 0,
                extrudedHeight: Math.max(evt.severity * 1500, 5000),
                material: evt.type === "FLOOD"
                    ? Cesium.Color.fromCssColorString("#0055ff").withAlpha(0.3)
                    : Cesium.Color.fromCssColorString("#ff6600").withAlpha(0.3),
                outline: true,
                outlineColor: evt.type === "FLOOD"
                    ? Cesium.Color.fromCssColorString("#00aaff").withAlpha(0.95)
                    : Cesium.Color.fromCssColorString("#ff3300").withAlpha(0.95),
                outlineWidth: 2,
            }
        });
    });

    // Render RouteOptimizer alternate polyline on map
    if (activePayload && activePayload.agent === "RouteOptimizer") {
        const alts = activePayload.calculated_alternatives;
        alts.forEach((alt, idx) => {
            if (alt.route_polyline && alt.route_polyline.length > 1) {
                viewer.entities.add({
                    id: `alt-route-${alt.option_id}-${idx}`,
                    name: `Alternate Route ${alt.option_id}`,
                    polyline: {
                        positions: Cesium.Cartesian3.fromDegreesArray(alt.route_polyline.flat()),
                        width: 5,
                        material: new Cesium.PolylineGlowMaterialProperty({
                            glowPower: 0.3,
                            color: Cesium.Color.fromCssColorString("#FACC15"),
                        }),
                    },
                });
            }
        });
    }

    // Focus on the disruption or impacted shipment when the agent is active.
    if (activePayload && (activePayload.agent === "RiskAnalyst" || activePayload.agent === "ActionComposer")) {
      const eventPolygon = activePayload.agent === "RiskAnalyst"
        ? activePayload.event.polygonGeoJSON[0]
        : disruptions[disruptions.length - 1]?.polygonGeoJSON?.[0];
      const center = eventPolygon?.[0];
      if (center) {
        viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(center[0], center[1], 120000),
            orientation: {
                heading: Cesium.Math.toRadians(15),
                pitch: Cesium.Math.toRadians(-40),
                roll: 0
            },
            duration: 3
        });
      }
    }

    return () => {
      window.clearTimeout(minorRoadTimer);
    };
  }, [shipments, disruptions, activePayload]);

  return (
    <div className="relative w-full h-full overflow-hidden">
      <div ref={containerRef} className="w-full h-full" />
      
      {/* Tactical HUD Overlay Elements on Map */}
      <div className="absolute top-6 left-6 flex flex-col gap-2 pointer-events-none">
        <div className="flex items-center gap-2 px-3 py-1 bg-black/60 border border-cyan-500/30 text-[10px] text-cyan-500 font-bold uppercase tracking-widest">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
            Live Map: Connected
        </div>
        <div className="px-3 py-1 bg-black/60 border border-cyan-500/30 text-[9px] text-zinc-400 font-mono">
            ZOOM: 5.2x | TILT: 0.0°
        </div>
      </div>

      <div className="absolute bottom-6 right-6 pointer-events-none">
        <div className="flex flex-col items-end gap-1">
            <div className="text-[10px] text-cyan-900 font-bold tracking-[0.5em] uppercase">LogosGotham</div>
            <div className="text-[8px] text-cyan-900/60 font-mono">v1.2.0-STABLE</div>
        </div>
      </div>

      {/* Crosshair */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-20">
        <div className="w-12 h-12 border border-cyan-500/50 rounded-full flex items-center justify-center">
            <div className="w-[1px] h-4 bg-cyan-500/50 absolute top-0" />
            <div className="w-[1px] h-4 bg-cyan-500/50 absolute bottom-0" />
            <div className="w-4 h-[1px] bg-cyan-500/50 absolute left-0" />
            <div className="w-4 h-[1px] bg-cyan-500/50 absolute right-0" />
        </div>
      </div>
    </div>
  );
}
