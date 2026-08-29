#!/bin/bash

#
# Docker Homebridge Custom Startup Script - oznu/homebridge
#
# This script can be used to customise the environment and will be executed as
# the root user each time the container starts.
#

# --- homebridge-plejd: rebuild its native Bluetooth module if the Node ABI changed ---
# The homebridge/homebridge image auto-updates and periodically bumps Node
# (22 -> 24 broke Plejd on 2026-06-29: "compiled against a different Node.js
# version ... NODE_MODULE_VERSION"). The plugin lives on the persistent
# /homebridge volume, so its compiled .node file goes stale. Build in /tmp
# because /homebridge is an Unraid /mnt/user FUSE share where node-gyp's
# clean step fails with ENOTEMPTY on hard-linked build artifacts.
NODE=/opt/homebridge/bin/node
PLEJD=/homebridge/node_modules/homebridge-plejd
HCI=$PLEJD/node_modules/@abandonware/bluetooth-hci-socket
if [ -d "$HCI" ] && ! "$NODE" -e "process.dlopen(module, process.argv[1])" "$HCI/build/Release/bluetooth_hci_socket.node" >/dev/null 2>&1; then
  echo "[startup.sh] bluetooth-hci-socket does not load on node $("$NODE" -v) - rebuilding"
  rm -rf /tmp/bhs && mkdir -p /tmp/bhs \
    && (cd "$HCI" && tar --exclude=./build -cf - .) | tar -xf - -C /tmp/bhs \
    && (cd /tmp/bhs && NODE_PATH="$PLEJD/node_modules" "$PLEJD/node_modules/.bin/node-pre-gyp" install --build-from-source >/tmp/bhs-build.log 2>&1) \
    && mkdir -p "$HCI/build/Release" \
    && cp -f /tmp/bhs/build/Release/bluetooth_hci_socket.node "$HCI/build/Release/bluetooth_hci_socket.node" \
    && echo "[startup.sh] bluetooth-hci-socket rebuilt OK" \
    || echo "[startup.sh] bluetooth-hci-socket rebuild FAILED - see /tmp/bhs-build.log in the container"
fi

# --- homebridge-plejd: local patches (hide scenes; make devices[].hidden stick) ---
# See /homebridge/patch-plejd.js. Idempotent; must re-run on every start because
# plugin updates overwrite dist/. If it fails the plugin still works, the hidden
# scenes/devices just reappear in HomeKit.
if [ -f /homebridge/patch-plejd.js ] && [ -d "$PLEJD" ]; then
  "$NODE" /homebridge/patch-plejd.js \
    || echo "[startup.sh] patch-plejd.js FAILED - plugin code changed? hidden scenes/devices will reappear"
fi
