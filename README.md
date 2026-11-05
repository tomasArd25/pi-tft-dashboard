# pi-tft-dashboard

A lightweight, always-on system monitor for **SPI TFT screens** (ILI9486 / GoodTFT 3.5") on a Raspberry Pi.
It shows CPU, RAM, temperature, disk, network and uptime as clean dark cards.

It renders with **Pillow** and writes RGB565 pixels directly to the framebuffer (`/dev/fb0`),
so it needs **no X11, no SDL/pygame and no desktop environment**.

## Hardware / OS tested

- Raspberry Pi 5, Raspberry Pi OS (Bookworm/Trixie, Python 3.13)
- 3.5" GPIO/SPI LCD (ILI9486) installed with GoodTFT's `LCD35-show`
  (`dtoverlay=tft35a:rotate=270`, shows up as `fb_ili9486` on `/dev/fb0`)

Confirm your display is on the framebuffer you expect:

```bash
cat /proc/fb          # e.g. "0 fb_ili9486"
ls /dev/fb*
```

## Install

```bash
git clone https://github.com/<your-username>/pi-tft-dashboard.git
cd pi-tft-dashboard
sudo ./install.sh
```

This installs the dependencies (`python3-psutil`, `python3-pil`, `python3-numpy`, `fonts-dejavu-core`),
copies the script to `/opt/pi-tft-dashboard`, and enables a systemd service that starts on every boot.

### Kiosk mode (optional)

```bash
sudo ./install.sh --kiosk
sudo reboot
```

Kiosk mode additionally:

- sets the default boot target to `multi-user.target` (no desktop)
- removes any `startx` line from `~/.bash_profile` (backup saved as `.bash_profile.pre-dashboard`)
- appends `logo.nologo quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0` to `/boot/firmware/cmdline.txt`
  (backup saved as `cmdline.txt.pre-dashboard`)

## Uninstall

```bash
sudo ./uninstall.sh            # remove the dashboard only
sudo ./uninstall.sh --kiosk    # also restore desktop, cmdline.txt and ~/.bash_profile
sudo reboot
```

## Configuration

Set environment variables in the service file (`Environment=KEY=value`), then
`sudo systemctl daemon-reload && sudo systemctl restart pi-tft-dashboard`.

| Variable        | Default     | Description               |
|-----------------|-------------|---------------------------|
| `DASH_FB`       | `/dev/fb0`  | Framebuffer device        |
| `DASH_WIDTH`    | `480`       | Framebuffer width (px)    |
| `DASH_HEIGHT`   | `320`       | Framebuffer height (px)   |
| `DASH_INTERVAL` | `2.0`       | Refresh interval (s)      |
| `DASH_TITLE`    | hostname    | Header text               |

## Troubleshooting

**Nothing shows on the TFT**
Check the service: `sudo systemctl status pi-tft-dashboard` and `journalctl -u pi-tft-dashboard -n 30`.
Make sure the display really is `/dev/fb0` (`cat /proc/fb`) and set `DASH_FB` if not.

**A desktop, cursor or console text is drawn over the dashboard / screen tearing**
Something else is also writing to the framebuffer. Check with `ps aux | grep -E 'Xorg|startx|lxsession'`.
A common cause is a `startx` line in `~/.bash_profile` launching the desktop on login. Remove it (or use `--kiosk`).

**`status=217/USER` in systemd**
The `User=` in the service file doesn't exist. The provided service runs as `root`, which is needed to write to `/dev/fb0`.

**pygame / tkinter don't work**
Expected on SPI framebuffer displays: `fbcon`/X11 backends are often unavailable. That is why this project writes to the framebuffer directly.

## How it works

1. Draws a 480x320 frame with Pillow
2. Converts RGB888 to RGB565 with NumPy
3. Writes the bytes to `/dev/fb0` every 2 seconds

## License

MIT
