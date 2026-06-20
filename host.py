#!/usr/bin/env python3
"""
Presentation Remote - Visual Demo
Shows a fake slide deck controlled by the ESP32 joystick remote.

Usage:
    pip install opencv-python pyserial
    python host.py              # auto-detect port
    python host.py /dev/ttyUSB0 # specify port
"""

import sys
import time
import threading
import serial
import serial.tools.list_ports
import numpy as np
import cv2

BAUD_RATE = 115200
WINDOW = "Presentation Remote Demo"
WIDTH, HEIGHT = 1280, 720

SLIDES = [
    {"title": "Wireless Presentation Remote", "subtitle": "ESP32 + ESP-NOW + Joystick", "color": (180, 60, 20)},
    {"title": "The Problem", "subtitle": "Clickers are boring and cost $40", "color": (30, 100, 180)},
    {"title": "Architecture", "subtitle": "Joystick -> ESP-NOW -> USB Serial -> PC", "color": (20, 130, 60)},
    {"title": "ESP-NOW", "subtitle": "Sub-millisecond, no WiFi network needed", "color": (140, 40, 120)},
    {"title": "Live Demo", "subtitle": "You're looking at it right now", "color": (40, 80, 160)},
    {"title": "Thanks!", "subtitle": "github.com/your-repo-here", "color": (60, 60, 60)},
]

current_slide = 0
last_command = ""
last_command_time = 0
joystick_dir = (0, 0)  # normalized x, y for visual indicator
lock = threading.Lock()


def find_serial_port():
    for port in serial.tools.list_ports.comports():
        desc = port.description.lower()
        if any(chip in desc for chip in ["cp210", "ch340", "ch910", "usb serial", "uart"]):
            return port.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def serial_thread(port):
    global current_slide, last_command, last_command_time, joystick_dir

    ser = serial.Serial(port, BAUD_RATE, timeout=1)
    time.sleep(2)

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception:
            break
        if not line or line == "READY":
            continue

        cmd = line.split()[-1] if line.split() else line

        with lock:
            last_command = cmd
            last_command_time = time.time()

            if cmd == "NEXT":
                current_slide = min(current_slide + 1, len(SLIDES) - 1)
                joystick_dir = (0, 1)
            elif cmd == "PREV":
                current_slide = max(current_slide - 1, 0)
                joystick_dir = (0, -1)
            elif cmd == "RIGHT":
                joystick_dir = (1, 0)
            elif cmd == "LEFT":
                joystick_dir = (-1, 0)
            elif cmd == "CLICK":
                joystick_dir = (0, 0)


def put_text_centered(img, text, y, scale, color, thickness):
    size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0]
    x = (img.shape[1] - size[0]) // 2
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_joystick_indicator(img, x, y, radius, dx, dy):
    cv2.circle(img, (x, y), radius, (80, 80, 80), 2, cv2.LINE_AA)
    knob_x = x + int(dx * radius * 0.6)
    knob_y = y + int(dy * radius * 0.6)
    cv2.circle(img, (knob_x, knob_y), radius // 3, (255, 255, 255), -1, cv2.LINE_AA)


def draw_slide(slide_idx):
    slide = SLIDES[slide_idx]
    b, g, r = slide["color"]
    img = np.full((HEIGHT, WIDTH, 3), (b, g, r), dtype=np.uint8)

    put_text_centered(img, slide["title"], HEIGHT // 2 - 30, 2.0, (255, 255, 255), 4)
    put_text_centered(img, slide["subtitle"], HEIGHT // 2 + 50, 0.9, (200, 200, 200), 2)

    # slide counter bottom-right
    counter = f"{slide_idx + 1} / {len(SLIDES)}"
    cv2.putText(img, counter, (WIDTH - 160, HEIGHT - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2, cv2.LINE_AA)

    # progress bar
    progress = (slide_idx + 1) / len(SLIDES)
    bar_w = int(WIDTH * progress)
    cv2.rectangle(img, (0, HEIGHT - 6), (bar_w, HEIGHT), (255, 255, 255), -1)

    with lock:
        dx, dy = joystick_dir
        cmd = last_command
        cmd_age = time.time() - last_command_time

    # joystick indicator bottom-left
    draw_joystick_indicator(img, 60, HEIGHT - 60, 30, dx, dy)

    # flash the command name briefly
    if cmd and cmd_age < 0.6:
        alpha = max(0.0, 1.0 - cmd_age / 0.6)
        overlay_color = (255, 255, 255)
        put_text_centered(img, cmd, HEIGHT - 80, 1.2,
                          tuple(int(c * alpha) for c in overlay_color), 3)

    return img


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    if not port:
        print("No serial port found. Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device}: {p.description}")
        sys.exit(1)

    print(f"Connecting to {port}...")
    t = threading.Thread(target=serial_thread, args=(port,), daemon=True)
    t.start()

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, WIDTH, HEIGHT)
    print("Window open. Press 'q' or ESC to quit. You can also use arrow keys to test.\n")

    global current_slide, last_command, last_command_time, joystick_dir

    while True:
        img = draw_slide(current_slide)
        cv2.imshow(WINDOW, img)

        key = cv2.waitKey(30) & 0xFF

        if key in (ord("q"), 27):
            break
        elif key == 83:  # right arrow
            with lock:
                current_slide = min(current_slide + 1, len(SLIDES) - 1)
                last_command, last_command_time = "NEXT", time.time()
        elif key == 81:  # left arrow
            with lock:
                current_slide = max(current_slide - 1, 0)
                last_command, last_command_time = "PREV", time.time()

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
