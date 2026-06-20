// Presentation Remote - Joystick Transmitter
// Reads analog joystick and sends commands to receiver via ESP-NOW
//
// Wiring:
//   Joystick VCC  -> 3.3V
//   Joystick GND  -> GND
//   Joystick VRx  -> GPIO 34
//   Joystick VRy  -> GPIO 35
//   Joystick SW   -> GPIO 32

#include <esp_now.h>
#include <WiFi.h>

#define JOY_X_PIN 34
#define JOY_Y_PIN 35
#define JOY_BTN_PIN 32
#define LED_PIN 2

#define CMD_NONE  0
#define CMD_NEXT  1
#define CMD_PREV  2
#define CMD_LEFT  3
#define CMD_RIGHT 4
#define CMD_CLICK 5

#define JOY_CENTER 2048
#define JOY_DEADZONE 600
#define SEND_COOLDOWN_MS 300

typedef struct {
  uint8_t command;
} message_t;

// Broadcast address — works without knowing receiver MAC
uint8_t receiverMAC[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

unsigned long lastSendTime = 0;
esp_now_peer_info_t peerInfo;

void onSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) {
    digitalWrite(LED_PIN, HIGH);
    delay(30);
    digitalWrite(LED_PIN, LOW);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(JOY_BTN_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  Serial.println("=== Presentation Remote (Transmitter) ===");
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed!");
    return;
  }

  esp_now_register_send_cb(onSent);

  memcpy(peerInfo.peer_addr, receiverMAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  Serial.println("Ready. Push joystick to send commands.");
}

uint8_t readJoystick() {
  int x = analogRead(JOY_X_PIN);
  int y = analogRead(JOY_Y_PIN);
  int btn = digitalRead(JOY_BTN_PIN);

  if (btn == LOW) return CMD_CLICK;

  if (x > JOY_CENTER + JOY_DEADZONE) return CMD_NEXT;
  if (x < JOY_CENTER - JOY_DEADZONE) return CMD_PREV;

  if (y > JOY_CENTER + JOY_DEADZONE) return CMD_RIGHT;
  if (y < JOY_CENTER - JOY_DEADZONE) return CMD_LEFT;

  return CMD_NONE;
}

const char* cmdName(uint8_t cmd) {
  switch (cmd) {
    case CMD_NEXT:  return "NEXT";
    case CMD_PREV:  return "PREV";
    case CMD_LEFT:  return "LEFT";
    case CMD_RIGHT: return "RIGHT";
    case CMD_CLICK: return "CLICK";
    default:        return "NONE";
  }
}

void loop() {
  uint8_t cmd = readJoystick();

  if (cmd != CMD_NONE && (millis() - lastSendTime > SEND_COOLDOWN_MS)) {
    message_t msg;
    msg.command = cmd;
    esp_now_send(receiverMAC, (uint8_t *)&msg, sizeof(msg));
    lastSendTime = millis();
    Serial.printf("Sent: %s\n", cmdName(cmd));
  }

  delay(20);
}
