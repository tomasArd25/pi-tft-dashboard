#!/usr/bin/env python3
"""
pi-tft-dashboard
A tiny system monitor for SPI TFT screens (ILI9486 / GoodTFT 3.5") on Raspberry Pi.
Renders with Pillow and writes RGB565 pixels straight to the framebuffer,
so no X11, SDL, or desktop is needed.

Config via environment variables:
  DASH_FB        framebuffer device   (default /dev/fb0)
  DASH_WIDTH     framebuffer width    (default 480)
  DASH_HEIGHT    framebuffer height   (default 320)
  DASH_INTERVAL  refresh seconds      (default 2.0)
  DASH_TITLE     header text          (default: hostname)
"""
import os
import socket
import subprocess
import time

import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageFont

FB = os.environ.get("DASH_FB", "/dev/fb0")
W = int(os.environ.get("DASH_WIDTH", 480))
H = int(os.environ.get("DASH_HEIGHT", 320))
INTERVAL = float(os.environ.get("DASH_INTERVAL", 2.0))
TITLE = os.environ.get("DASH_TITLE", socket.gethostname())

# Hide the blinking console cursor (best effort)
os.system("echo 0 > /sys/class/graphics/fbcon/cursor_blink 2>/dev/null")

BLACK = (17, 17, 17)
CARD = (30, 30, 30)
WHITE = (220, 220, 220)
MUTED = (100, 100, 100)
BLUE = (55, 138, 221)
GREEN = (29, 158, 117)
AMBER = (239, 159, 39)
PURPLE = (127, 119, 221)
RED = (226, 75, 74)

try:
    FONT_BIG = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 28)
    FONT_MED = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14)
    FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11)
except OSError:
    FONT_BIG = FONT_MED = FONT_SMALL = ImageFont.load_default()


def get_temp():
    """CPU temperature in °C. Tries vcgencmd, falls back to sysfs."""
    try:
        r = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True)
        return float(r.stdout.strip().replace("temp=", "").replace("'C", ""))
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return float(f.read()) / 1000.0
        except Exception:
            return 0.0


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))  # no packet is actually sent
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def format_uptime(seconds):
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m {s}s"


def to_rgb565(arr):
    r = (arr[:, :, 0] >> 3).astype("uint16")
    g = (arr[:, :, 1] >> 2).astype("uint16")
    b = (arr[:, :, 2] >> 3).astype("uint16")
    return ((r << 11) | (g << 5) | b).tobytes()


def draw_card(d, x, y, w, h):
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=CARD, outline=(60, 60, 60))


def draw_bar(d, x, y, w, h, pct, color):
    d.rounded_rectangle([x, y, x + w, y + h], radius=3, fill=(45, 45, 45))
    fw = int(w * min(max(pct, 0), 100) / 100)
    if fw > 4:
        d.rounded_rectangle([x, y, x + fw, y + h], radius=3, fill=color)


def main():
    psutil.cpu_percent(percpu=True)  # prime the counter
    time.sleep(0.5)

    cached_ip = get_ip()
    loops_since_ip = 0
    old_net = psutil.net_io_counters()
    old_time = time.time()

    while True:
        loop_start = time.time()

        cpu_cores = psutil.cpu_percent(interval=0.5, percpu=True)
        cpu = sum(cpu_cores) / len(cpu_cores)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        temp = get_temp()

        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - old_time, 0.001)
        tx = max((net.bytes_sent - old_net.bytes_sent) / dt / 1024 / 1024, 0)
        rx = max((net.bytes_recv - old_net.bytes_recv) / dt / 1024 / 1024, 0)
        old_net, old_time = net, now

        loops_since_ip += 1
        if loops_since_ip >= 30:  # refresh IP roughly once a minute
            cached_ip = get_ip()
            loops_since_ip = 0

        uptime = format_uptime(int(time.time() - psutil.boot_time()))
        temp_color = RED if temp > 70 else AMBER if temp > 60 else GREEN

        img = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(img)

        d.text((10, 5), TITLE, font=FONT_MED, fill=WHITE)
        d.text((370, 7), time.strftime("%H:%M:%S"), font=FONT_SMALL, fill=MUTED)

        CW, CH, M = 148, 88, 8

        # CPU
        draw_card(d, M, 26, CW, CH)
        d.text((M + 10, 32), "CPU", font=FONT_SMALL, fill=MUTED)
        d.text((M + 10, 46), f"{cpu:.0f}%", font=FONT_BIG, fill=BLUE)
        d.text((M + 10, 80), f"{len(cpu_cores)} cores", font=FONT_SMALL, fill=MUTED)
        draw_bar(d, M + 10, 106, CW - 20, 6, cpu, BLUE)

        # RAM
        draw_card(d, M + CW + 8, 26, CW, CH)
        d.text((M + CW + 18, 32), "RAM", font=FONT_SMALL, fill=MUTED)
        d.text((M + CW + 18, 46), f"{ram.percent:.0f}%", font=FONT_BIG, fill=GREEN)
        d.text((M + CW + 18, 80), f"{ram.used / 1024**3:.1f}/{ram.total / 1024**3:.1f}GB",
               font=FONT_SMALL, fill=MUTED)
        draw_bar(d, M + CW + 18, 106, CW - 20, 6, ram.percent, GREEN)

        # Temp
        draw_card(d, M, 126, CW, CH)
        d.text((M + 10, 132), "TEMP", font=FONT_SMALL, fill=MUTED)
        d.text((M + 10, 146), f"{temp:.1f}C", font=FONT_BIG, fill=temp_color)
        status = "HOT!" if temp > 70 else "WARM" if temp > 60 else "OK"
        d.text((M + 10, 180), status, font=FONT_SMALL, fill=temp_color)
        draw_bar(d, M + 10, 206, CW - 20, 6, temp, temp_color)

        # Disk
        draw_card(d, M + CW + 8, 126, CW, CH)
        d.text((M + CW + 18, 132), "DISK", font=FONT_SMALL, fill=MUTED)
        d.text((M + CW + 18, 146), f"{disk.percent:.0f}%", font=FONT_BIG, fill=PURPLE)
        d.text((M + CW + 18, 180), f"{disk.used / 1024**3:.1f}/{disk.total / 1024**3:.1f}GB",
               font=FONT_SMALL, fill=MUTED)
        draw_bar(d, M + CW + 18, 206, CW - 20, 6, disk.percent, PURPLE)

        # Network
        draw_card(d, M, 226, 304, 52)
        d.text((M + 10, 232), "NETWORK", font=FONT_SMALL, fill=MUTED)
        d.text((M + 10, 246), cached_ip, font=FONT_MED, fill=WHITE)
        d.text((M + 190, 250), f"u:{tx:.1f} d:{rx:.1f} MB/s", font=FONT_SMALL, fill=MUTED)

        # Uptime
        draw_card(d, M, 288, 304, 26)
        d.text((M + 10, 294), f"up  {uptime}", font=FONT_SMALL, fill=MUTED)

        with open(FB, "wb") as fb:
            fb.write(to_rgb565(np.array(img)))

        time.sleep(max(INTERVAL - (time.time() - loop_start), 0))


if __name__ == "__main__":
    main()
