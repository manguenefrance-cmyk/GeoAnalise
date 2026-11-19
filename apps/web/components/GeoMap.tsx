"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MapType, GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Crosshair, Layers, MousePointer2, MapPin } from "lucide-react";
import type { Area, Analysis } from "@/lib/api";
import { api } from "@/lib/api";
import { useApp } from "@/lib/context";

type Props = {
  area: Area | undefined;
  points: number[][];
  drawing: boolean;
  onPoint: (point: number[]) => void;
  result: Analysis | undefined;
  opacity: number;
};
export default function GeoMap({
  area,
  points,
  drawing,
  onPoint,
  result,
  opacity,
}: Props) {
  const { t, token } = useApp();
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<MapType | null>(null);
  const props = useRef({ drawing, onPoint, result, token });
  props.current = { drawing, onPoint, result, token };
  const [loaded, setLoaded] = useState(false);
  const [pixel, setPixel] = useState<number[] | null>(null);
  const [showArea, setShowArea] = useState(true);
  const [mapError, setMapError] = useState(false);
  useEffect(() => {
    if (!host.current) return;
    let instance: MapType;
    try {
      maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
      instance = new maplibregl.Map({
        container: host.current,
        center: [32.576, -25.95],
        zoom: 12,
        style:
          process.env.NEXT_PUBLIC_MAP_STYLE ||
          "https://tiles.openfreemap.org/styles/positron",
        transformRequest: (url) =>
          url.includes("/api/v1/artifacts/")
            ? {
                url,
                headers: { Authorization: `Bearer ${props.current.token}` },
              }
            : { url },
      });
    } catch {
      setMapError(true);
      return;
    }
    map.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(host.current);
    instance.addControl(
      new maplibregl.NavigationControl({ visualizePitch: true }),
      "top-right",
    );
    instance.addControl(
      new maplibregl.ScaleControl({ unit: "metric" }),
      "bottom-left",
    );
    instance.on("load", () => setLoaded(true));
    instance.on("click", async (e) => {
      if (props.current.drawing) {
        props.current.onPoint([e.lngLat.lng, e.lngLat.lat]);
        return;
      }
      const cog = props.current.result?.artifacts.find(
        (a) => a.artifact_type === "cog",
      );
      if (cog) {
        try {
          const data = await api<{ values: number[] }>(
            `/v1/artifacts/${cog.id}/pixel?lon=${e.lngLat.lng}&lat=${e.lngLat.lat}`,
            props.current.token,
          );
          setPixel(data.values);
        } catch {
          setPixel(null);
        }
      }
    });
    return () => {
      observer.disconnect();
      instance.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    const instance = map.current;
    if (!loaded || !instance) return;
    const features: GeoJSON.Feature[] = [];
    if (area)
      features.push({
        type: "Feature",
        properties: {},
        geometry: area.geometry,
      });
    if (points.length >= 3)
      features.push({
        type: "Feature",
        properties: {},
        geometry: { type: "Polygon", coordinates: [[...points, points[0]]] },
      });
    else if (points.length)
      features.push({
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: points },
      });
    const data: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features,
    };
    if (instance.getSource("aoi"))
      (instance.getSource("aoi") as GeoJSONSource).setData(data);
    else {
      instance.addSource("aoi", { type: "geojson", data });
      instance.addLayer({
        id: "aoi-fill",
        type: "fill",
        source: "aoi",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": "#087f77", "fill-opacity": 0.08 },
      });
      instance.addLayer({
        id: "aoi-line",
        type: "line",
        source: "aoi",
        paint: {
          "line-color": "#087f77",
          "line-width": 2.5,
          "line-dasharray": [3, 2],
        },
      });
    }
  }, [loaded, area, points]);
  useEffect(() => {
    if (!loaded || !map.current || !area) return;
    zoomArea(); /* area reference is the viewport trigger */
  }, [loaded, area]);
  function zoomArea() {
    const instance = map.current;
    if (!instance || !area) return;
    const geom = area.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
    const coords =
      geom.type === "Polygon"
        ? geom.coordinates.flat()
        : geom.coordinates.flat(2);
    const bounds = new maplibregl.LngLatBounds();
    coords.forEach((c) => bounds.extend(c as [number, number]));
    instance.fitBounds(bounds, { padding: 90, maxZoom: 16, duration: 600 });
  }
  useEffect(() => {
    const instance = map.current;
    if (!loaded || !instance) return;
    if (instance.getLayer("analysis")) instance.removeLayer("analysis");
    if (instance.getSource("analysis")) instance.removeSource("analysis");
    const artifact =
      result?.status === "succeeded"
        ? result.artifacts.find((a) => a.artifact_type === "cog")
        : undefined;
    if (artifact) {
      instance.addSource("analysis", {
        type: "raster",
        tiles: [
          `${window.location.origin}/api/v1/artifacts/${artifact.id}/tiles/{z}/{x}/{y}.png`,
        ],
        tileSize: 256,
      });
      instance.addLayer(
        {
          id: "analysis",
          type: "raster",
          source: "analysis",
          paint: { "raster-opacity": opacity, "raster-fade-duration": 0 },
        },
        instance.getLayer("aoi-line") ? "aoi-line" : undefined,
      );
    }
    setPixel(null);
  }, [loaded, result?.id, result?.status]);
  useEffect(() => {
    if (map.current?.getLayer("analysis"))
      map.current.setPaintProperty("analysis", "raster-opacity", opacity);
  }, [opacity]);
  useEffect(() => {
    if (!loaded || !map.current) return;
    for (const id of ["aoi-fill", "aoi-line"])
      if (map.current.getLayer(id))
        map.current.setLayoutProperty(
          id,
          "visibility",
          showArea ? "visible" : "none",
        );
  }, [showArea, loaded]);
  useEffect(() => {
    if (map.current)
      map.current.getCanvas().style.cursor = drawing ? "crosshair" : "";
  }, [drawing]);
  return (
    <div className="map-shell">
      <div className="map-canvas" ref={host} />
      {mapError && (
        <div className="map-fallback">
          <MapPin size={30} />
          <p>{t.mapView}</p>
          <p>{t.coordinates}</p>
        </div>
      )}
      <div className="map-top-label">
        <span className="status-dot" />
        {drawing ? t.drawHelp : t.mapView}
      </div>
      <div className="map-tools">
        <button title={t.zoomArea} aria-label={t.zoomArea} onClick={zoomArea}>
          <Crosshair size={19} />
        </button>
        <button
          title={t.aoiLayer}
          aria-label={t.aoiLayer}
          aria-pressed={showArea}
          onClick={() => setShowArea(!showArea)}
        >
          <Layers size={19} />
        </button>
      </div>
      {drawing && (
        <div className="drawing-label">
          <MousePointer2 size={16} />
          {points.length} {t.coordinates.toLowerCase()}
        </div>
      )}
      {pixel && (
        <div className="pixel-label">
          {t.pixel}:{" "}
          {pixel.map((v) => (v === null ? t.noData : v.toFixed(5))).join(", ")}
        </div>
      )}
      <div className="map-coordinate">
        32.576° E &nbsp; 25.950° S <span>WGS 84</span>
      </div>
    </div>
  );
}
