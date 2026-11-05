#!/usr/bin/env bash
# Usage: sudo ./install.sh [--kiosk]
#   --kiosk  also disable the desktop, hide boot text and the console cursor
set -euo pipefail

KIOSK=0
[[ "${1:-}" == "--kiosk" ]] && KIOSK=1

if [[ $EUID -ne 0 ]]; then
  echo "Please run with sudo: sudo ./install.sh [--kiosk]"; exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR=/opt/pi-tft-dashboard
SERVICE=pi-tft-dashboard.service
CMDLINE=/boot/firmware/cmdline.txt
TARGET_USER="${SUDO_USER:-root}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

echo "==> Installing dependencies"
apt-get update
apt-get install -y python3-psutil python3-pil python3-numpy fonts-dejavu-core

echo "==> Installing dashboard to $INSTALL_DIR"
install -d "$INSTALL_DIR"
install -m 755 "$HERE/dashboard.py" "$INSTALL_DIR/dashboard.py"
install -m 644 "$HERE/$SERVICE" "/etc/systemd/system/$SERVICE"

systemctl daemon-reload
systemctl enable --now "$SERVICE"
echo "==> Dashboard service enabled and started"

if [[ $KIOSK -eq 1 ]]; then
  echo "==> Applying kiosk mode"

  # 1. Quiet boot + hidden cursor (backup first, only once)
  if [[ -f "$CMDLINE" ]]; then
    [[ -f "$CMDLINE.pre-dashboard" ]] || cp "$CMDLINE" "$CMDLINE.pre-dashboard"
    if ! grep -q "vt.global_cursor_default=0" "$CMDLINE"; then
      sed -i '1 s/$/ logo.nologo quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0/' "$CMDLINE"
    fi
  fi

  # 2. Boot to console instead of desktop
  systemctl set-default multi-user.target

  # 3. Stop auto-starting the desktop from the login profile
  PROFILE="$TARGET_HOME/.bash_profile"
  if [[ -f "$PROFILE" ]] && grep -q "startx" "$PROFILE"; then
    [[ -f "$PROFILE.pre-dashboard" ]] || cp "$PROFILE" "$PROFILE.pre-dashboard"
    sed -i '/startx/d' "$PROFILE"
  fi

  echo "==> Kiosk mode applied. Reboot to see the final result: sudo reboot"
fi

echo "Done."
