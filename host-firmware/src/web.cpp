#include "web.h"

#include <ArduinoJson.h>
#include <WebServer.h>

#include "console.h"
#include "display.h"
#include "settings.h"

namespace {

WebServer server(80);

String htmlEscape(const String& in) {
  String out;
  out.reserve(in.length());
  for (size_t i = 0; i < in.length(); i++) {
    const char c = in[i];
    if (c == '<') out += F("&lt;");
    else if (c == '>') out += F("&gt;");
    else if (c == '&') out += F("&amp;");
    else out += c;
  }
  return out;
}

void redirectHome() {
  server.sendHeader("Location", "/");
  server.send(303);
}

void sendJson(int status, const JsonDocument& doc) {
  String body;
  serializeJson(doc, body);
  server.send(status, "application/json", body);
}

void sendJsonError(int status, const char* error) {
  JsonDocument doc;
  doc["ok"] = false;
  doc["error"] = error;
  sendJson(status, doc);
}

void sendResult(const display::SendResult& result) {
  JsonDocument doc;
  doc["ok"] = true;
  doc["sent"] = result.sent;
  doc["failed"] = result.failed;
  doc["speed"] = result.speed;
  sendJson(200, doc);
}

void handlePage() {
  const Settings& cfg = settings::get();
  char range[24];
  snprintf(range, sizeof(range), "0x%02X..0x%02X", settings::unitAddress(0), settings::unitAddress(cfg.numSymbols - 1));

  String html;
  html.reserve(6000);
  html += F(R"HTML(<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Split-flap</title>
<style>
body{font-family:sans-serif;max-width:640px;margin:1rem auto;padding:0 1rem}
label{display:block;margin:.6rem 0}input{display:block;padding:.4rem;width:8rem}
button{padding:.5rem 1rem;margin-right:.5rem}
pre{background:#111;color:#cfc;padding:.6rem;height:18rem;overflow:auto;font-size:.8rem}
</style></head><body><h2>Split-flap host</h2>
<form method="post" action="/settings">
<label>Number of symbols (1-10)<input type="number" name="num_symbols" min="1" max="10" value=")HTML");
  html += cfg.numSymbols;
  html += F("\"></label><label>Default speed (1-");
  html += MAX_ROTATION_SPEED;
  html += F(")<input type=\"number\" name=\"default_speed\" min=\"1\" max=\"");
  html += MAX_ROTATION_SPEED;
  html += F("\" value=\"");
  html += cfg.defaultSpeed;
  html += F("\"></label><label>First unit address (switch value 0-15)<input type=\"number\" name=\"first_unit_address\" min=\"0\" max=\"15\" value=\"");
  html += cfg.firstUnitAddress;
  html += F("\"></label><p>I2C range: ");
  html += range;
  html += F(R"HTML(</p><button type="submit">Save</button></form>
<form method="post" action="/scan" style="margin:1rem 0"><button type="submit">Scan for slaves</button></form>
<h3>Console log</h3><pre id="log">)HTML");
  html += htmlEscape(console::dump());
  html += F(R"HTML(</pre><script>
var l=document.getElementById('log');l.scrollTop=l.scrollHeight;
setInterval(function(){fetch('/api/log').then(function(r){return r.text()}).then(function(t){l.textContent=t;l.scrollTop=l.scrollHeight})},3000);
</script></body></html>)HTML");

  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "text/html", html);
}

void handleLog() {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "text/plain", console::dump());
}

void handleSettings() {
  settings::apply(server.arg("num_symbols").toInt(), server.arg("default_speed").toInt(),
                  server.arg("first_unit_address").toInt());
  const Settings& cfg = settings::get();
  console::print("settings saved: symbols=%u speed=%u first=%u", cfg.numSymbols, cfg.defaultSpeed,
                 cfg.firstUnitAddress);
  redirectHome();
}

void handleScan() {
  display::scan();
  redirectHome();
}

void handleMessage() {
  JsonDocument doc;
  if (deserializeJson(doc, server.arg("plain"))) {
    sendJsonError(400, "invalid json");
    return;
  }
  if (!doc["message"].is<const char*>()) {
    sendJsonError(400, "message is required");
    return;
  }

  long speed = -1;
  JsonVariant speedValue = doc["speed"];
  if (speedValue.is<long>()) {
    speed = speedValue.as<long>();
  } else if (speedValue.is<const char*>()) {
    speed = atol(speedValue.as<const char*>());
  }

  sendResult(display::sendMessage(doc["message"].as<String>(), speed));
}

void handleClear() {
  sendResult(display::clear());
}

}  // namespace

namespace web {

void begin() {
  server.on("/", HTTP_GET, handlePage);
  server.on("/api/log", HTTP_GET, handleLog);
  server.on("/settings", HTTP_POST, handleSettings);
  server.on("/scan", HTTP_POST, handleScan);
  server.on("/api/message", HTTP_POST, handleMessage);
  server.on("/api/clear", HTTP_POST, handleClear);
  server.begin();
}

void handleClient() {
  server.handleClient();
}

}  // namespace web
