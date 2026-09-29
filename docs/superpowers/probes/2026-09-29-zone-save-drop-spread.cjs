// Make every handleEditZone call site pass only what it sets.
// Run from custom_components/irrigation_plus/frontend.
const fs = require("fs");
const file = "src/views/zones/view-zone-settings.ts";
const spread = /this\.handleEditZone\(\s*index\s*,\s*\{\s*\.\.\.zone\b/g;
let src = fs.readFileSync(file, "utf8");
const before = (src.match(spread) || []).length;
// The plant-type handler builds its change in `next` and spread both.
src = src.replace(
  /(this\.handleEditZone\(\s*index\s*,\s*)\{\s*\.\.\.zone\s*,\s*\.\.\.next\s*\}/g,
  "$1next",
);
// Every other call site: drop the `...zone,` at the head of its object.
src = src.replace(/(this\.handleEditZone\(\s*index\s*,\s*\{)\s*\.\.\.zone\s*,/g, "$1");
const after = (src.match(spread) || []).length;
fs.writeFileSync(file, src);
console.log(`...zone spreads: before=${before} after=${after}`);
