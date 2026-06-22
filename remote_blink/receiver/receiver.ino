// ESP-NOW receiver – LED mirrors sender's button state.

#include <esp_now.h>
#include <WiFi.h>

#define LED_PIN 2

typedef struct { bool on; } Message;

volatile bool ledState = false;
volatile bool stateChanged = false;

void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len == sizeof(Message)) {
    Message msg;
    memcpy(&msg, data, sizeof(msg));
    ledState = msg.on;
    stateChanged = true;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);
  Serial.print("Receiver MAC: ");
  Serial.println(WiFi.macAddress());

  esp_now_init();
  esp_now_register_recv_cb(onReceive);

  Serial.println("Waiting for commands...");
}

void loop() {
  if (stateChanged) {
    stateChanged = false;
    digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    Serial.println(ledState ? "LED on" : "LED off");
  }
}
