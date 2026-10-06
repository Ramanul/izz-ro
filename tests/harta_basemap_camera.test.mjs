import test from "node:test";
import assert from "node:assert/strict";
import { cameraForView, projectionForMap } from "../static/harta-stiri/basemap-camera.mjs";

const projection = {
  source_crs: "EPSG:4326",
  projection: {
    lon_min: 20,
    lon_max: 30,
    lat_min: 40,
    lat_max: 50,
    width: 1000,
    height: 700,
    method: "equirectangular_cos_latitude_reference",
  },
};
const fullView = "0 0 1000 700";

function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance,
    `${actual} differs from ${expected} by more than ${tolerance}`);
}

test("projection metadata is accepted only for the matching EPSG:4326 SVG viewBox", () => {
  const geo = projectionForMap(projection, fullView);
  assert.ok(geo);
  assert.equal(geo.vx, 0);
  assert.equal(geo.viewWidth, 1000);
  assert.equal(projectionForMap({ ...projection, source_crs: "EPSG:3857" }, fullView), null);
  assert.equal(projectionForMap(projection, "0 0 900 700"), null);
  assert.equal(projectionForMap({
    ...projection,
    projection: { ...projection.projection, method: "unknown" },
  }, fullView), null);
});

test("full-view camera is centered on published geographic bounds", () => {
  const geo = projectionForMap(projection, fullView);
  const camera = cameraForView({ x: 0, y: 0, width: 1000, height: 700 }, geo, 700);
  assert.ok(camera);
  close(camera.center[0], 25);
  close(camera.center[1], 45);
  assert.ok(camera.zoom >= 2 && camera.zoom <= 19);
  assert.ok(camera.scaleY >= 0.85 && camera.scaleY <= 1.15);
});

test("SVG zoom and viewport resizing move MapLibre by the matching scale", () => {
  const geo = projectionForMap(projection, fullView);
  const full = cameraForView({ x: 0, y: 0, width: 1000, height: 700 }, geo, 700);
  const half = cameraForView({ x: 250, y: 175, width: 500, height: 350 }, geo, 700);
  const wider = cameraForView({ x: 0, y: 0, width: 1000, height: 700 }, geo, 1400);
  assert.ok(full && half && wider);
  close(half.center[0], full.center[0]);
  close(half.center[1], full.center[1]);
  close(half.zoom, full.zoom + 1);
  close(wider.zoom, full.zoom + 1);
});

test("invalid views and unusable viewport sizes return no camera", () => {
  const geo = projectionForMap(projection, fullView);
  assert.equal(cameraForView(null, geo, 700), null);
  assert.equal(cameraForView({ x: 0, y: 0, width: 0, height: 700 }, geo, 700), null);
  assert.equal(cameraForView({ x: 0, y: 0, width: 1000, height: 700 }, geo, 0), null);
});
