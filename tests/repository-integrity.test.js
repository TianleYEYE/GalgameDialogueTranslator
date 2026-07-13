import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("Tauri overlay configuration points to the bundled overlay page", async () => {
  const config = JSON.parse(await readFile(new URL("../src-tauri/tauri.conf.json", import.meta.url), "utf8"));
  const overlay = config.app.windows.find((window) => window.label === "translation-overlay");
  assert.equal(overlay?.url, "overlay.html");
  const html = await readFile(new URL("../public/overlay.html", import.meta.url), "utf8");
  assert.match(html, /start_translation_overlay_drag_command/);
  assert.match(html, /save_translation_overlay_bounds_command/);
  assert.match(html, /get_translation_overlay_state_command/);
});

test("Vue owns only the main application UI", async () => {
  const app = await readFile(new URL("../src/App.vue", import.meta.url), "utf8");
  assert.doesNotMatch(app, /v-if="isOverlayWindow"/);
});

test("native overlay maintenance reads capture state before changing it", async () => {
  const rust = await readFile(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
  assert.match(rust, /GetWindowDisplayAffinity/);
  assert.match(rust, /WindowEvent::Moved/);
  assert.match(rust, /WindowEvent::Resized/);
});

test("IDE metadata remains ignored", async () => {
  const ignore = await readFile(new URL("../.gitignore", import.meta.url), "utf8");
  assert.match(ignore, /^\.idea\/$/m);
});
