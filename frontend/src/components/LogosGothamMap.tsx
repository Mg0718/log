"use client";

import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import "cesium/Source/Widgets/widgets.css";
import { useLogisticsStore } from "@/store/useLogisticsStore";

// Cesium needs to know where its assets are
if (typeof window !== "undefined") {
    (window as any).CESIUM_BASE_URL = "/cesium";
    // Set global tokens if available
    if (process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN) {
        Cesium.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;
    }
}

export default function LogosGothamMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const { shipments, disruptions, activePayload } = useLogisticsStore();

  // 1. Initialize Viewer
  useEffect(() => {
    if (!containerRef.current) return;

    // 2. Initialize the viewer synchronously. By default, this uses Bing Maps Satellite imagery!
    const viewer = new Cesium.Viewer(containerRef.current, {
      timeline: true,           // Shows the time slider at the bottom
      animation: true,          // Shows the play/pause controls
      baseLayerPicker: false,   // Hides the map-style switcher to keep the UI clean
      geocoder: false,          // Hides the search bar
      homeButton: false,        // Hides the home button
      navigationHelpButton: false,
      fullscreenButton: false,
      vrButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      scene3DOnly: true,
      shadows: true,
    });

    // Dark mode aesthetics for background but satellite for globe
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#050505");
    viewer.scene.globe.depthTestAgainstTerrain = true;

    // Lock camera over India
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(78.9629, 20.5937, 4500000),
      duration: 0, // 0 means instant snap on load
    });

    viewerRef.current = viewer;

    async function setupTerrain() {
      // 3. Add 3D Terrain (Mountains, valleys) so it's not a flat sphere
      try {
        const terrainProvider = await Cesium.createWorldTerrainAsync();
        if (viewerRef.current && !viewerRef.current.isDestroyed()) {
            viewerRef.current.terrainProvider = terrainProvider;
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

    // Render Shipments
    shipments.forEach((shp) => {
      viewer.entities.add({
        id: shp.id,
        name: shp.cargo,
        position: Cesium.Cartesian3.fromDegrees(shp.currentRoute[0][0], shp.currentRoute[0][1]),
        point: {
          pixelSize: 10,
          color: shp.riskScore > 50 ? Cesium.Color.RED : Cesium.Color.CYAN,
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
          positions: Cesium.Cartesian3.fromDegreesArray(shp.currentRoute.flat()),
          width: 2,
          material: shp.riskScore > 50 ? Cesium.Color.RED.withAlpha(0.5) : Cesium.Color.CYAN.withAlpha(0.3),
        }
      });
    });

    // Render Disruption Polygons as 3D Volumes
    disruptions.forEach((evt) => {
        const flatCoords = evt.polygonGeoJSON[0].flat();
        viewer.entities.add({
            id: evt.id,
            name: evt.type,
            polygon: {
                hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                extrudedHeight: evt.severity * 1000,
                material: evt.type === "FLOOD" 
                    ? Cesium.Color.BLUE.withAlpha(0.4) 
                    : Cesium.Color.ORANGE.withAlpha(0.4),
                outline: true,
                outlineColor: Cesium.Color.WHITE.withAlpha(0.5),
            }
        });
    });

    // Cinematic Camera Fly-to on Payload
    if (activePayload && activePayload.agent === "RiskAnalyst") {
        const evt = activePayload.event;
        const center = evt.polygonGeoJSON[0][0];
        viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(center[0], center[1], 15000),
            orientation: {
                heading: Cesium.Math.toRadians(0),
                pitch: Cesium.Math.toRadians(-45),
                roll: 0
            },
            duration: 3
        });
    }
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
