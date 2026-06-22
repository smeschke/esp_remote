// ESP-NOW sender – holds button to keep receiver's LED on.

#include <esp_now.h>
#include <WiFi.h>

uint8_t receiverMac[] = {0xC0, 0xCD, 0xD6, 0xCA, 0x2B, 0xB4};

#define BUTTON_PIN 33
#define LED_PIN     2

typedef struct { bool on; } Message;

bool lastButtonState = HIGH;

void onSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Sent OK" : "Send FAIL");
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);
  Serial.print("Sender MAC: ");
  Serial.println(WiFi.macAddress());

  esp_now_init();
  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, receiverMac, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
}

void loop() {
  bool btn = digitalRead(BUTTON_PIN);
  if (btn != lastButtonState) {
    delay(20);
    btn = digitalRead(BUTTON_PIN);
    if (btn != lastButtonState) {
      lastButtonState = btn;
      bool pressed = (btn == LOW);
      Message msg = {pressed};
      esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
      digitalWrite(LED_PIN, pressed ? HIGH : LOW);
      Serial.println(pressed ? "Button pressed – LED on" : "Button released – LED off");
    }
  }
  delay(10);
}
