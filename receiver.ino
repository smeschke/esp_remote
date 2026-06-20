// Presentation Remote - USB Receiver
// Receives commands via ESP-NOW and sends them over Serial to the host PC
//
// Plug this ESP32 into the computer's USB port.
// Run host.py on the computer to translate serial commands into keypresses.

#include <esp_now.h>
#include <WiFi.h>

#define LED_PIN 2

#define CMD_NONE  0
#define CMD_NEXT  1
#define CMD_PREV  2
#define CMD_LEFT  3
#define CMD_RIGHT 4
#define CMD_CLICK 5

typedef struct {
  uint8_t command;
} message_t;

void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(message_t)) return;

  message_t msg;
  memcpy(&msg, data, sizeof(msg));

  digitalWrite(LED_PIN, HIGH);

  switch (msg.command) {
    case CMD_NEXT:  Serial.println("NEXT");  break;
    case CMD_PREV:  Serial.println("PREV");  break;
    case CMD_LEFT:  Serial.println("LEFT");  break;
    case CMD_RIGHT: Serial.println("RIGHT"); break;
    case CMD_CLICK: Serial.println("CLICK"); break;
  }

  delay(30);
  digitalWrite(LED_PIN, LOW);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  Serial.println("=== Presentation Remote (Receiver) ===");
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed!");
    return;
  }

  esp_now_register_recv_cb(onReceive);
  Serial.println("READY");
}

void loop() {
  delay(10);
}
