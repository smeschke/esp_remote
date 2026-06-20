# esp_remote
code for esp32+joystick remote control
**  ESP32 Presentation Remote

  Wireless presentation remote using two ESP32s and an analog joystick. One ESP32 reads the joystick and transmits commands over ESP-NOW. The other plugs into your computer via USB and forwards commands over serial.

  Hardware

  Transmitter (battery-powered):
  - ESP32
  - Analog joystick module
    - VRx → GPIO 34
    - VRy → GPIO 35
    - SW → GPIO 32
    - VCC → 3.3V
    - GND → GND

  Receiver (USB to computer):
  - ESP32 plugged into USB

  Setup

  Flash remote/remote.ino to the transmitter and receiver/receiver.ino to the receiver using Arduino IDE.

  Install Python dependencies:
  pip install opencv-python pyserial numpy

  Usage

  Slide deck demo — fake slides controlled by the joystick:
  python host.py              # auto-detect serial port
  python host.py /dev/ttyUSB0 # specify port

  3D ball demo — rotate a shaded sphere in real time:
  python ball.py

  Arrow keys work as a fallback in both demos. Press q or ESC to quit.

  How it works

  Joystick → ESP-NOW (wireless) → USB Serial → Python

  The joystick maps to five commands: NEXT, PREV, LEFT, RIGHT, CLICK. ESP-NOW delivers them in under a millisecond with no WiFi network required.
**
