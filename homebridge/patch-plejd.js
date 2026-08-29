#!/usr/bin/env node
// Local patches for homebridge-plejd (1.13.x) so accessories can actually be hidden.
//
// 1. PATCH(show_scenes)    - adds config options to hide Plejd scenes:
//      "show_scenes": false            -> hides all scenes
//      "hidden_scenes": ["Name", ...]  -> hides scenes by title
//    Stock plugin exposes every cloud scene and only honours "hidden from scene
//    list" set in the Plejd app.
// 2. PATCH(hidden_devices) - makes `devices[].hidden: true` stick. Stock plugin
//    keeps hidden devices in userInputConfig.devices (with a uuid), so
//    onPlejdUpdates() re-creates the accessory the moment the mesh reports that
//    device's state, and discoverDevices() never removes its cached accessory.
//    Filtering them out fixes both: updates are ignored and stale cache entries
//    are removed automatically ("Removing N stale accessories").
//
// Idempotent (marker comment per patch). Re-run by /homebridge/startup.sh on every
// container start because plugin updates overwrite dist/. Exits 1 if an anchor is
// missing (plugin code changed) - the other patches are still applied.

const fs = require('fs');
const file = '/homebridge/node_modules/homebridge-plejd/dist/PlejdHbPlatform.js';

const patches = [
  {
    mark: 'PATCH(show_scenes)',
    anchor:
`                if (siteScene.hiddenFromSceneList) {
                    return;
                }
`,
    replace: (anchor, mark) => anchor +
`                // ${mark}: local patch, re-applied by /homebridge/startup.sh (see patch-plejd.js)
                if (config.show_scenes === false || (config.hidden_scenes || []).includes(siteScene.title)) {
                    this.log.info(\`Hiding scene "\${siteScene.title}" (show_scenes/hidden_scenes config)\`);
                    return;
                }
`,
  },
  {
    mark: 'PATCH(hidden_devices)',
    anchor:
`            devices: devices.filter((device) => device.outputType === "LIGHT" ||
                device.outputType === "RELAY" ||
                device.outputType === "SENSOR"),
`,
    replace: (_anchor, mark) =>
`            // ${mark}: drop hidden devices entirely so BLE updates cannot re-create them (see patch-plejd.js)
            devices: devices.filter((device) => !device.hidden && (device.outputType === "LIGHT" ||
                device.outputType === "RELAY" ||
                device.outputType === "SENSOR")),
`,
  },
];

let src;
try { src = fs.readFileSync(file, 'utf8'); }
catch (e) { console.log(`[patch-plejd] ${file} not found - plugin not installed?`); process.exit(0); }

let changed = false, failed = false;
for (const p of patches) {
  if (src.includes(p.mark)) { console.log(`[patch-plejd] ${p.mark}: already applied`); continue; }
  if (!src.includes(p.anchor)) { console.error(`[patch-plejd] ${p.mark}: anchor not found - plugin code changed, NOT applied`); failed = true; continue; }
  src = src.replace(p.anchor, p.replace(p.anchor, p.mark));
  console.log(`[patch-plejd] ${p.mark}: applied`);
  changed = true;
}
if (changed) fs.writeFileSync(file, src);
process.exit(failed ? 1 : 0);
