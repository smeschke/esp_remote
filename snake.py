#!/usr/bin/env python3
"""
Snake Game - ESP32 Joystick Edition
Classic snake controlled by the ESP32 joystick remote or arrow keys.

Usage:
    pip install opencv-python pyserial numpy
    python snake.py              # auto-detect port
    python snake.py /dev/ttyUSB0 # specify port
"""

import sys
import time
import random
import threading
import serial
import serial.tools.list_ports
import numpy as np
import cv2

BAUD_RATE = 115200
WINDOW = "Snake - Joystick Control"
WIDTH, HEIGHT = 800, 800
CELL = 20
COLS = WIDTH // CELL
ROWS = HEIGHT // CELL
FPS = 5

lock = threading.Lock()
pending_cmd = None


def find_serial_port():
    for port in serial.tools.list_ports.comports():
        desc = port.description.lower()
        if any(chip in desc for chip in ["cp210", "ch340", "ch910", "usb serial", "uart"]):
            return port.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def serial_thread(port):
    global pending_cmd
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
            pending_cmd = cmd


def spawn_food(snake):
    while True:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in snake:
            return pos


def draw(snake, food, score, game_over):
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

    # checkerboard background
    for r in range(ROWS):
        for c in range(COLS):
            if (r + c) % 2 == 0:
                shade = 25
            else:
                shade = 18
            cv2.rectangle(img,
                          (c * CELL, r * CELL),
                          ((c + 1) * CELL, (r + 1) * CELL),
                          (shade, shade, shade), -1)

    # food
    fx, fy = food
    cx = fx * CELL + CELL // 2
    cy = fy * CELL + CELL // 2
    cv2.circle(img, (cx, cy), CELL // 2 - 2, (0, 0, 220), -1, cv2.LINE_AA)
    cv2.circle(img, (cx - 2, cy - 2), CELL // 6, (60, 60, 255), -1, cv2.LINE_AA)

    # snake
    for i, (sx, sy) in enumerate(snake):
        if i == len(snake) - 1:
            color = (0, 220, 80)
        else:
            t = i / max(len(snake) - 1, 1)
            color = (int(40 + 60 * t), int(140 + 80 * t), int(40 + 40 * t))
        x1 = sx * CELL + 1
        y1 = sy * CELL + 1
        x2 = (sx + 1) * CELL - 1
        y2 = (sy + 1) * CELL - 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1, cv2.LINE_AA)

    # eyes on the head
    hx, hy = snake[-1]
    head_cx = hx * CELL + CELL // 2
    head_cy = hy * CELL + CELL // 2
    cv2.circle(img, (head_cx - 3, head_cy - 3), 2, (0, 0, 0), -1)
    cv2.circle(img, (head_cx + 3, head_cy - 3), 2, (0, 0, 0), -1)

    # score
    cv2.putText(img, f"Score: {score}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

    if game_over:
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        cv2.putText(img, "GAME OVER", (WIDTH // 2 - 150, HEIGHT // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 255), 4, cv2.LINE_AA)
        cv2.putText(img, f"Score: {score}", (WIDTH // 2 - 80, HEIGHT // 2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(img, "Press SPACE to restart or Q to quit",
                    (WIDTH // 2 - 240, HEIGHT // 2 + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2, cv2.LINE_AA)

    return img


def calibrate():
    global pending_cmd

    steps = [
        ("UP", (0, -1)),
        ("DOWN", (0, 1)),
        ("LEFT", (-1, 0)),
        ("RIGHT", (1, 0)),
    ]
    mapping = {}
    done_labels = []

    for label, game_dir in steps:
        pending_cmd = None
        time.sleep(0.3)
        with lock:
            pending_cmd = None

        while True:
            img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
            cv2.putText(img, "CALIBRATION", (WIDTH // 2 - 180, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 200, 100), 3, cv2.LINE_AA)
            cv2.putText(img, f"Press {label} on the joystick",
                        (WIDTH // 2 - 280, HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
            for i, dl in enumerate(done_labels):
                cv2.putText(img, dl, (WIDTH // 2 - 100, HEIGHT // 2 + 60 + i * 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1, cv2.LINE_AA)
            cv2.imshow(WINDOW, img)

            key = cv2.waitKey(50) & 0xFF
            if key in (ord("q"), 27):
                return None

            with lock:
                cmd = pending_cmd
                pending_cmd = None

            if cmd and cmd not in mapping:
                mapping[cmd] = game_dir
                done_labels.append(f"{label} = {cmd}")
                break

    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    cv2.putText(img, "READY!", (WIDTH // 2 - 80, HEIGHT // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 200, 100), 3, cv2.LINE_AA)
    for i, dl in enumerate(done_labels):
        cv2.putText(img, dl, (WIDTH // 2 - 100, HEIGHT // 2 + 40 + i * 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 100), 1, cv2.LINE_AA)
    cv2.imshow(WINDOW, img)
    cv2.waitKey(1000)

    return mapping


def main():
    global pending_cmd

    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    has_serial = False
    if port:
        print(f"Connecting to {port}...")
        t = threading.Thread(target=serial_thread, args=(port,), daemon=True)
        t.start()
        has_serial = True
    else:
        print("No serial port found — keyboard-only mode (arrow keys).")

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, WIDTH, HEIGHT)

    if has_serial:
        cmd_map = calibrate()
        if cmd_map is None:
            cv2.destroyAllWindows()
            return
    else:
        cmd_map = {}

    while True:
        snake = [(COLS // 2, ROWS // 2)]
        direction = (1, 0)
        food = spawn_food(snake)
        score = 0
        game_over = False
        pending_cmd = None

        while True:
            with lock:
                cmd = pending_cmd
                pending_cmd = None

            new_dir = cmd_map.get(cmd) if cmd else None

            if new_dir and not game_over:
                dx, dy = direction
                ndx, ndy = new_dir
                if (ndx, ndy) != (-dx, -dy):
                    direction = new_dir

            if not game_over:
                hx, hy = snake[-1]
                nx = hx + direction[0]
                ny = hy + direction[1]

                if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS or (nx, ny) in snake:
                    game_over = True
                else:
                    snake.append((nx, ny))
                    if (nx, ny) == food:
                        score += 1
                        food = spawn_food(snake)
                    else:
                        snake.pop(0)

            img = draw(snake, food, score, game_over)
            cv2.imshow(WINDOW, img)

            key = cv2.waitKey(1000 // FPS) & 0xFF
            if key in (ord("q"), 27):
                cv2.destroyAllWindows()
                return
            elif key == ord(" ") and game_over:
                break
            elif key == 82:  # up
                with lock:
                    pending_cmd = "KB_UP"
                cmd_map["KB_UP"] = (0, -1)
            elif key == 84:  # down
                with lock:
                    pending_cmd = "KB_DOWN"
                cmd_map["KB_DOWN"] = (0, 1)
            elif key == 81:  # left
                with lock:
                    pending_cmd = "KB_LEFT"
                cmd_map["KB_LEFT"] = (-1, 0)
            elif key == 83:  # right
                with lock:
                    pending_cmd = "KB_RIGHT"
                cmd_map["KB_RIGHT"] = (1, 0)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
