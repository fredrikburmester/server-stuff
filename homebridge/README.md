# Homebridge on Unraid (Plejd over Bluetooth)

Container: `homebridge/homebridge:ubuntu`, appdata `/mnt/user/appdata/homebridge`
→ `/homebridge`. Runs with `--net=host --privileged` and `/dev/hci0` passed
through. Plugins: `homebridge-plejd` (child bridge, BLE via `@abandonware/noble`)
and `@milo526/homebridge-tuya-web`.

Bluetooth adapter: USB CSR dongle `0a12:0001` → `hci0` on the host. The host has
`hciconfig` / `bluetoothd` from NerdPack, but **bluetoothd is intentionally not
run** — noble talks to `hci0` over a raw HCI socket and bluetoothd competes with it.

## Two things that must hold for Plejd to work

1. **`hci0` must be UP.** noble never brings the adapter up itself and nothing
   on Unraid does it for you, so after a host boot (or a dongle reset) Plejd
   silently sits at `poweredOff`.
   → [`boot-bluetooth`](boot-bluetooth) runs as the User Script `bluetooth-boot`
   every 5 min (`*/5 * * * *`, idempotent). Check: `hciconfig hci0` → `UP RUNNING`.
2. **The plugin's native module must match the container's Node ABI.** The
   Homebridge image auto-updates weekly and periodically bumps Node
   (22 → 24 on 2026-06-24). `bluetooth_hci_socket.node` lives on the persistent
   volume, so it goes stale and the plugin fails with
   `compiled against a different Node.js version ... NODE_MODULE_VERSION`.
   → [`startup.sh`](startup.sh) (= `/homebridge/startup.sh`, runs on every
   container start) test-loads the module and rebuilds it if it fails.

## Why the rebuild is done in `/tmp`

`/homebridge` is an Unraid `/mnt/user` FUSE (shfs) share. `npm rebuild` /
`node-gyp rebuild` fail there with `ENOTEMPTY: rmdir 'build/Release'`: node-gyp
hard-links the build output and shfs leaves a `.fuse_hidden*` placeholder behind
while the old binary is still mapped by the running Homebridge process. The
startup script therefore copies the package to `/tmp`, builds it with
`node-pre-gyp install --build-from-source` (plain `node-gyp` fails with
`Undefined variable module_name in binding.gyp`), and copies only the resulting
`.node` file back. Restarting the container clears any leftover `.fuse_hidden*`.

## Manual recovery

```bash
# on the Unraid host
hciconfig hci0 up
docker exec homebridge bash /homebridge/startup.sh   # rebuilds only if needed
docker restart homebridge
docker logs --since 2m homebridge | grep -i plejd     # expect "Noble State changed: poweredOn"
```

## Hiding accessories (done 2026-08-29)

Only these are exposed to HomeKit: Plejd lights **Köksvägg, Köksön, Badrum tak,
Badrum spegel**; Tuya **Vardagsrum hörn, Vardagsrum Fönster** (one device, two
outlets), **Sovrum Säng**. Configured in `config.json`:

- Plejd: `"show_buttons": false` (hides every wall-button + the "Plejd Remote"
  accessory) and `"devices": [{ "identifier": N, "hidden": true, ... }]` for
  Vardagsrum 1 (11), Hall (15), Sovrum 2 (17), Sovrum 1 (33). Identifiers are
  Plejd output addresses — read them from `accessories/cachedAccessories.<PlejdBridge>`.
- Tuya: `"hiddenAccessories": [<tuya id>, ...]`.
- Plejd scenes: `"show_scenes": false` — **this option only exists thanks to a
  local patch**, see below.

### Runbook: getting a device back / adding new ones

Currently hidden Plejd devices (identifier → what it is):

| id | name | model | what |
|----|------|-------|------|
| 11 | Vardagsrum 1 | DIM-01 | dimmer, living room |
| 15 | Hall | DIM-01 | dimmer, hallway |
| 17 | Sovrum 2 | DIM-01 | dimmer, bedroom |
| 33 | Sovrum 1 | SPR-01 | **smart plug/outlet**, bedroom |

Hidden Tuya: `TV` (65580202d8f15be13793), `Hall` (084704042462ab44fba6),
`Sovrum Fönster` (bff3063f41f332dfe759gb).

- **Want a hidden Plejd device back** (e.g. the Sovrum 1 outlet): open
  `config.json` (Homebridge UI → Settings → JSON Config, or
  `/mnt/user/appdata/homebridge/config.json`), **delete that device's whole
  entry** from the Plejd `devices` array, restart Homebridge. The plugin
  re-adds it from the Plejd cloud with the right name/type. Don't just flip
  `hidden` to `false` — a non-hidden manual entry overrides the cloud data and
  you get the "missing type field" warning.
- **Want a hidden Tuya device back:** remove its id from `hiddenAccessories`,
  restart.
- **New Plejd device added in the Plejd app:** nothing to do — it is exposed
  automatically on the next Homebridge restart. Only the identifiers listed
  above are hidden.
- **Want to hide another Plejd device:** find its identifier (it is in
  `accessories/cachedAccessories.0E1D366D893B` as `context.device.identifier`,
  or in the plugin's debug log), add
  `{ "name": "…", "type": "Light", "model": "…", "identifier": N, "hidden": true }`
  to `devices`, restart. The patched plugin removes the stale accessory itself.
- **Want scenes or buttons back:** set `show_scenes` / `show_buttons` to `true`
  (or use `"hidden_scenes": ["Title", …]` to hide only some).

Restart = `docker restart homebridge` on Unraid, or the restart button in the
Homebridge UI (http://192.168.1.105:8581). Then check
`docker logs --since 3m homebridge | grep -i plejd` for `Removing … stale` /
`Connection fully established`.

### Local plugin patch — [`patch-plejd.js`](patch-plejd.js)

Stock homebridge-plejd 1.13.2 can't really hide things:

- Scenes are always exposed (`hidden: false` hard-coded; it only honours "hidden
  from scene list" set in the Plejd app).
- `devices[].hidden: true` is only half-implemented: the hidden device stays in
  `userInputConfig.devices` with a UUID, so (a) its cached accessory is never
  removed as stale and (b) `onPlejdUpdates()` re-creates the accessory the moment
  the mesh reports that light's state — it silently comes back.

`/homebridge/patch-plejd.js` inserts two small changes into
`dist/PlejdHbPlatform.js`: a `show_scenes` / `hidden_scenes` check in scene
extraction, and `!device.hidden` in the device filter. With both, the plugin
logs `Hiding scene …` / `… is set to hidden` and then `Removing N stale
accessories` by itself. `startup.sh` re-runs the patch on every container start
(plugin updates overwrite `dist/`); it is idempotent and refuses to touch the
file if an anchor no longer matches — then the hidden things simply reappear
and the patch needs updating for the new plugin version.

One leftover the patch doesn't cover: "Plejd Remote" stays cached after
`show_buttons: false` (buttons list is still non-empty). It was pruned once by
hand from `accessories/cachedAccessories.0E1D366D893B`; the plugin does not
re-add it. Tuya removes its hidden accessories by itself.

Files on the host:
- `/mnt/user/appdata/homebridge/startup.sh`
- `/boot/config/plugins/user.scripts/scripts/bluetooth-boot/script`
- `/boot/config/plugins/user.scripts/customSchedule.cron` (the `*/5` entry; User
  Scripts regenerates it from `schedule.json` when you save in the UI)
