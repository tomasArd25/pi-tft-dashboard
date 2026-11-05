#!/usr/bin/env bash
# Usage: sudo ./uninstall.sh [--kiosk]
#   --kiosk  also undo the kiosk changes (desktop, cmdline.txt, ~/.bash_profile)
set -euo pipefail

REVERT_KIOSK=0
[[ "${1:-}" == "--kiosk" ]] && REVERT_KIOSK=1

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./uninstall.sh [--kiosk]"; exit 1
fi

SERVICE=pi-tft-dashboard.service
CMDLINE=/boot/firmware/cmdline.txt
TARGET_USER="${SUDO_USER:-root}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

echo "==> Removing service and files"
systemctl disable --now "$SERVICE" 2>/dev/null || true
rm -f "/etc/systemd/system/$SERVICE"
systemctl daemon-reload
rm -rf /opt/pi-tft-dashboard

if [[ $REVERT_KIOSK -eq 1 ]]; then
  echo "==> Reverting kiosk changes"

  if [[ -f "$CMDLINE.pre-dashboard" ]]; then
    cp "$CMDLINE.pre-dashboard" "$CMDLINE"
    rm "$CMDLINE.pre-dashboard"
  fi

  systemctl set-default graphical.target

  PROFILE="$TARGET_HOME/.bash_profile"
  if [[ -f "$PROFILE.pre-dashboard" ]]; then
    cp "$PROFILE.pre-dashboard" "$PROFILE"
    rm "$PROFILE.pre-dashboard"
  fi

  echo "==> Reboot to return to the normal desktop: sudo reboot"
fi

echo "Done. (apt packages were left installed; remove them manually if you want.)"
