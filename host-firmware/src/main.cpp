#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>

#include "console.h"
#include "display.h"
#include "settings.h"
#include "web.h"

void setup() {
  console::begin();
  settings::load();
  display::begin();
  console::print("boot");

  WiFiManager wm;
  wm.setDebugOutput(ENABLE_SERIAL_LOG);
  wm.setConnectTimeout(20);
  // Without a timeout a router outage at boot would leave the host stuck in the portal.
  wm.setConfigPortalTimeout(180);
  if (!wm.autoConnect("SplitFlap-Setup")) {
    console::print("wifi connect failed, restarting");
    delay(1000);
    ESP.restart();
  }
  console::print("wifi connected, ip %s", WiFi.localIP().toString().c_str());

  display::scan();
  web::begin();
}

void loop() {
  web::handleClient();
}
