import assert from "node:assert/strict";
import test from "node:test";

import { buildOverlayGeometry, finiteNumberOrNull, normalizeOverlayBounds } from "../src/overlay-state.js";

const game = { x: 100, y: 50, width: 1200, height: 700 };
const crop = { left: 0.1, top: 0.65, right: 0.9, bottom: 0.95 };

test("buildOverlayGeometry positions a new overlay relative to the selected game", () => {
  const geometry = buildOverlayGeometry({ game, crop, fontSize: "20" });
  assert.equal(geometry.x, 220);
  assert.equal(geometry.width, 960);
  assert.equal(geometry.height, 96);
  assert.equal(geometry.y, 401);
});

test("buildOverlayGeometry preserves manually saved bounds", () => {
  const geometry = buildOverlayGeometry({
    game,
    crop,
    fontSize: "20",
    savedBounds: { x: 420, y: 180, width: 640, height: 120 }
  });
  assert.deepEqual(geometry, { x: 420, y: 180, width: 640, height: 120 });
});

test("normalizeOverlayBounds rejects invalid persisted values", () => {
  assert.deepEqual(normalizeOverlayBounds({ x: "15", y: "bad", width: 500, height: null }), {
    x: 15,
    y: null,
    width: 500,
    height: null
  });
  assert.equal(finiteNumberOrNull(undefined), null);
});
