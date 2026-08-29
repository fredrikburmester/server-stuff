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

Files on the host:
- `/mnt/user/appdata/homebridge/startup.sh`
- `/boot/config/plugins/user.scripts/scripts/bluetooth-boot/script`
- `/boot/config/plugins/user.scripts/customSchedule.cron` (the `*/5` entry; User
  Scripts regenerates it from `schedule.json` when you save in the UI)
