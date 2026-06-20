#!/usr/bin/env python3
"""
3D Ball Control Demo
Rotate a shaded sphere with the ESP32 joystick.
Demonstrates continuous real-time control over ESP-NOW.

Usage:
    pip install opencv-python pyserial numpy
    python ball.py              # auto-detect port
    python ball.py /dev/ttyUSB0 # specify port
"""

import sys
import time
import math
import threading
import serial
import serial.tools.list_ports
import numpy as np
import cv2

BAUD_RATE = 115200
WINDOW = "3D Ball - Joystick Control"
SIZE = 1700
BALL_RADIUS = 200
CENTER = SIZE // 2

# rotation state (radians)
rot_x = 0.0
rot_y = 0.0
joy_dx = 0.0
joy_dy = 0.0
lock = threading.Lock()


def find_serial_port():
    for port in serial.tools.list_ports.comports():
        desc = port.description.lower()
        if any(chip in desc for chip in ["cp210", "ch340", "ch910", "usb serial", "uart"]):
            return port.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def serial_thread(port):
    global joy_dx, joy_dy

    ser = serial.Serial(port, BAUD_RATE, timeout=0.05)
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
            if cmd == "NEXT":
                joy_dy = 1.0
            elif cmd == "PREV":
                joy_dy = -1.0
            elif cmd == "RIGHT":
                joy_dx = 1.0
            elif cmd == "LEFT":
                joy_dx = -1.0
            elif cmd == "CLICK":
                joy_dx = 0.0
                joy_dy = 0.0


def rotate_point(x, y, z, ax, ay):
    # rotate around X axis
    cos_a, sin_a = math.cos(ax), math.sin(ax)
    y2 = y * cos_a - z * sin_a
    z2 = y * sin_a + z * cos_a
    # rotate around Y axis
    cos_b, sin_b = math.cos(ay), math.sin(ay)
    x2 = x * cos_b + z2 * sin_b
    z3 = -x * sin_b + z2 * cos_b
    return x2, y2, z3


def draw_ball(rx, ry):
    img = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)

    # draw latitude/longitude lines on a sphere
    light_dir = np.array([0.4, -0.5, 0.8])
    light_dir = light_dir / np.linalg.norm(light_dir)

    # shaded sphere using pixel-level normals
    ys, xs = np.ogrid[-BALL_RADIUS:BALL_RADIUS + 1, -BALL_RADIUS:BALL_RADIUS + 1]
    dist_sq = xs * xs + ys * ys
    mask = dist_sq <= BALL_RADIUS * BALL_RADIUS

    zs = np.sqrt(np.clip(BALL_RADIUS * BALL_RADIUS - dist_sq, 0, None))
    nx = xs / BALL_RADIUS
    ny = ys / BALL_RADIUS
    nz = zs / BALL_RADIUS

    # rotate normals
    cos_rx, sin_rx = math.cos(rx), math.sin(rx)
    cos_ry, sin_ry = math.cos(ry), math.sin(ry)

    ny2 = ny * cos_rx - nz * sin_rx
    nz2 = ny * sin_rx + nz * cos_rx
    nx2 = nx * cos_ry + nz2 * sin_ry
    nz3 = -nx * sin_ry + nz2 * cos_ry

    # diffuse lighting
    dot = nx2 * light_dir[0] + ny2 * light_dir[1] + nz3 * light_dir[2]
    diffuse = np.clip(dot, 0, 1)

    # specular highlight
    spec = np.clip(dot, 0, 1) ** 32 * 0.6

    # grid lines: use rotated coordinates to compute lat/lon
    # original sphere coordinates before rotation
    orig_x = nx
    orig_y = ny
    orig_z = nz

    # inverse rotate to get texture coordinates
    inx = orig_x * cos_ry - orig_z * sin_ry
    inz = orig_x * sin_ry + orig_z * cos_ry
    iny2 = orig_y * cos_rx + inz * sin_rx
    inz2 = -orig_y * sin_rx + inz * cos_rx

    lat = np.arcsin(np.clip(iny2, -1, 1))
    lon = np.arctan2(inx, inz2)

    lat_lines = np.abs(np.mod(lat * 6 / math.pi + 0.5, 1.0) - 0.5)
    lon_lines = np.abs(np.mod(lon * 6 / math.pi + 0.5, 1.0) - 0.5)
    on_grid = (lat_lines < 0.04) | (lon_lines < 0.04)

    # base color
    base_r = diffuse * 60 + spec * 255
    base_g = diffuse * 160 + spec * 255
    base_b = diffuse * 255 + spec * 255

    # grid overlay
    grid_r = np.where(on_grid, np.clip(base_r + 60, 0, 255), base_r)
    grid_g = np.where(on_grid, np.clip(base_g + 40, 0, 255), base_g)
    grid_b = np.where(on_grid, np.clip(base_b + 20, 0, 255), base_b)

    ambient = 25
    r = np.clip(grid_r + ambient, 0, 255).astype(np.uint8)
    g = np.clip(grid_g + ambient, 0, 255).astype(np.uint8)
    b = np.clip(grid_b + ambient, 0, 255).astype(np.uint8)

    y_start = CENTER - BALL_RADIUS
    x_start = CENTER - BALL_RADIUS
    roi = img[y_start:y_start + 2 * BALL_RADIUS + 1, x_start:x_start + 2 * BALL_RADIUS + 1]
    roi[mask] = np.stack([b[mask], g[mask], r[mask]], axis=-1)

    # shadow
    shadow_y = CENTER + BALL_RADIUS + 40
    cv2.ellipse(img, (CENTER, shadow_y), (BALL_RADIUS - 20, 18), 0, 0, 360, (15, 15, 15), -1, cv2.LINE_AA)

    # rotation readout
    deg_x = math.degrees(rx) % 360
    deg_y = math.degrees(ry) % 360
    cv2.putText(img, f"X: {deg_x:.0f}  Y: {deg_y:.0f}", (20, SIZE - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 120, 120), 1, cv2.LINE_AA)

    return img


def main():
    global rot_x, rot_y, joy_dx, joy_dy

    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    if port:
        print(f"Connecting to {port}...")
        t = threading.Thread(target=serial_thread, args=(port,), daemon=True)
        t.start()
    else:
        print("No serial port found — keyboard-only mode (arrow keys).")

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, SIZE, SIZE)

    ROT_SPEED = 0.05
    DECAY = 0.5
    vx, vy = 0.0, 0.0

    while True:
        with lock:
            dx, dy = joy_dx, joy_dy
            joy_dx *= 0.7
            joy_dy *= 0.7
            if abs(joy_dx) < 0.05:
                joy_dx = 0
            if abs(joy_dy) < 0.05:
                joy_dy = 0

        vx = vx * DECAY + dy * ROT_SPEED
        vy = vy * DECAY + dx * ROT_SPEED
        rot_x += vx
        rot_y += vy

        img = draw_ball(rot_x, rot_y)
        cv2.imshow(WINDOW, img)

        key = cv2.waitKey(16) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == 82:  # up
            vx -= ROT_SPEED * 3
        elif key == 84:  # down
            vx += ROT_SPEED * 3
        elif key == 81:  # left
            vy -= ROT_SPEED * 3
        elif key == 83:  # right
            vy += ROT_SPEED * 3

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
