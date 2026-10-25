#include "web.h"

#include <ArduinoJson.h>
#include <Update.h>
#include <WebServer.h>

#include "console.h"
#include "display.h"
#include "net.h"
#include "settings.h"
#include "version.h"

#ifndef UPDATE_PASSWORD
#error "Define UPDATE_PASSWORD in build_flags"
#endif

namespace {

constexpr const char* kUpdateUser = "admin";

WebServer server(80);
bool uploadAllowed = false;

bool authorized() {
  if (server.authenticate(kUpdateUser, UPDATE_PASSWORD)) {
    return true;
  }
  server.requestAuthentication();
  return false;
}

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

void addRow(String& html, const char* label, const char* hint, const String& input) {
  html += F("<label class=\"row\"><span>");
  html += label;
  html += F("<small>");
  html += hint;
  html += F("</small></span>");
  html += input;
  html += F("</label>");
}

String numberInput(const char* name, long low, long high, long value) {
  String s = F("<input type=\"number\" name=\"");
  s += name;
  s += F("\" min=\"");
  s += low;
  s += F("\" max=\"");
  s += high;
  s += F("\" value=\"");
  s += value;
  s += F("\">");
  return s;
}

String textInput(const char* name, const String& value, int maxLength) {
  String s = F("<input type=\"text\" name=\"");
  s += name;
  s += F("\" maxlength=\"");
  s += maxLength;
  s += F("\" value=\"");
  s += value;
  s += F("\">");
  return s;
}

void handlePage() {
  const Settings& cfg = settings::get();
  char range[24];
  snprintf(range, sizeof(range), "0x%02X..0x%02X", settings::unitAddress(0), settings::unitAddress(cfg.numSymbols - 1));
  char tcaAddress[8];
  snprintf(tcaAddress, sizeof(tcaAddress), "0x%02X", cfg.tcaAddress);
  char speedHint[24];
  snprintf(speedHint, sizeof(speedHint), "1-%d", MAX_ROTATION_SPEED);
  char rangeHint[48];
  snprintf(rangeHint, sizeof(rangeHint), "Switch value 0-15, units %s", range);

  String html;
  html.reserve(9000);
  html += F(R"HTML(<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Split-flap</title>
<style>
:root{--bg:#f3f5f8;--card:#fff;--text:#16202a;--muted:#5d6b7a;--line:#d9e0e8;--accent:#0c6a8c}
@media(prefers-color-scheme:dark){:root{--bg:#10161c;--card:#18212a;--text:#e6edf3;--muted:#8b9aa9;--line:#2a3541;--accent:#2a9bc4}}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
header{background:var(--accent);color:#fff;padding:1rem}
header h1{margin:0 auto;max-width:640px;font-size:1.25rem}
main{max-width:640px;margin:1rem auto;padding:0 1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:1rem;margin-bottom:1rem}
.card h2{margin:0 0 .6rem;font-size:1rem}
.row{display:grid;grid-template-columns:1fr 9rem;gap:.5rem;align-items:center;margin:.7rem 0}
.row small{display:block;color:var(--muted);font-size:.8rem}
input[type=number],input[type=text]{width:100%;padding:.5rem;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--text);font-size:1rem}
input[type=checkbox]{width:1.3rem;height:1.3rem;justify-self:start}
.actions{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1rem}
button{background:var(--accent);color:#fff;border:1px solid var(--accent);border-radius:6px;padding:.6rem 1.2rem;font-size:1rem;cursor:pointer}
button.secondary{background:transparent;color:var(--accent)}
pre{background:#0d1117;color:#b6f3c0;padding:.7rem;border-radius:6px;height:16rem;overflow:auto;font-size:.78rem;margin:0}
footer{text-align:center;color:var(--muted);font-size:.8rem;padding:0 1rem 1.5rem}
footer a{color:var(--accent)}
@media(max-width:480px){.row{grid-template-columns:1fr}}
</style></head><body><header><h1>Split-flap host</h1></header><main>
<form method="post" action="/settings">
<section class="card"><h2>Display</h2>)HTML");
  addRow(html, "Number of symbols", "1-10", numberInput("num_symbols", 1, kMaxUnits, cfg.numSymbols));
  addRow(html, "Default speed", speedHint, numberInput("default_speed", 1, MAX_ROTATION_SPEED, cfg.defaultSpeed));
  addRow(html, "First unit address", rangeHint, numberInput("first_unit_address", 0, kMaxSwitchValue, cfg.firstUnitAddress));
  html += F("</section><section class=\"card\"><h2>I2C multiplexer (TCA9548A)</h2>");
  addRow(html, "Use multiplexer", "Off when units are wired directly",
         String(F("<input type=\"checkbox\" name=\"tca_enabled\"")) + (cfg.tcaEnabled ? F(" checked>") : F(">")));
  addRow(html, "Address", "e.g. 0x70", textInput("tca_address", tcaAddress, 6));
  addRow(html, "Channels", "Comma-separated, 0-7", textInput("tca_channels", settings::channelsText(), 20));
  html += F("</section><section class=\"card\"><h2>Network</h2>");
  addRow(html, "Hostname", "Reachable as hostname.local", textInput("hostname", cfg.hostname, 31));
  html += F(R"HTML(</section>
<div class="actions"><button type="submit">Save settings</button>
<button type="submit" formaction="/scan" class="secondary">Scan for slaves</button></div>
</form>
<section class="card"><h2>Console log</h2><pre id="log">)HTML");
  html += htmlEscape(console::dump());
  html += F(R"HTML(</pre></section></main>
<footer>Firmware )HTML");
  html += BUILD_TAG;
  html += F(R"HTML( &middot; <a href="/update">update</a></footer>
<script>
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
  const String oldHostname = settings::get().hostname;
  SettingsInput input;
  input.numSymbols = server.arg("num_symbols").toInt();
  input.defaultSpeed = server.arg("default_speed").toInt();
  input.firstUnitAddress = server.arg("first_unit_address").toInt();
  input.hostname = server.arg("hostname");
  input.tcaEnabled = server.hasArg("tca_enabled");
  input.tcaAddress = server.arg("tca_address");
  input.tcaChannels = server.arg("tca_channels");
  settings::apply(input);
  const Settings& cfg = settings::get();
  console::print("settings saved: symbols=%u speed=%u first=%u", cfg.numSymbols, cfg.defaultSpeed,
                 cfg.firstUnitAddress);
  if (oldHostname != cfg.hostname) {
    net::startMdns();
  }
  display::scan();
  redirectHome();
}

void handleUpdatePage() {
  if (!authorized()) return;
  server.send(200, "text/html",
              F("<!doctype html><html><head><meta charset=\"utf-8\"><title>Update</title></head><body>"
                "<h2>Firmware update</h2><form method=\"post\" action=\"/update\" enctype=\"multipart/form-data\">"
                "<input type=\"file\" name=\"firmware\" accept=\".bin\" required> "
                "<button type=\"submit\">Upload</button></form><p><a href=\"/\">Back</a></p></body></html>"));
}

void handleUpdateDone() {
  if (!authorized()) return;
  const bool ok = !Update.hasError();
  server.send(ok ? 200 : 500, "text/plain", ok ? "Update OK, rebooting" : "Update failed");
  if (ok) {
    delay(500);
    ESP.restart();
  }
}

void handleUpdateUpload() {
  HTTPUpload& upload = server.upload();
  if (upload.status == UPLOAD_FILE_START) {
    uploadAllowed = server.authenticate(kUpdateUser, UPDATE_PASSWORD);
    if (!uploadAllowed) return;
    console::print("firmware update started: %s", upload.filename.c_str());
    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
      console::print("update begin failed: %s", Update.errorString());
    }
  } else if (!uploadAllowed) {
    return;
  } else if (upload.status == UPLOAD_FILE_WRITE) {
    if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
      console::print("update write failed: %s", Update.errorString());
    }
  } else if (upload.status == UPLOAD_FILE_END) {
    if (Update.end(true)) {
      console::print("firmware update ok, %u bytes", static_cast<unsigned>(upload.totalSize));
    } else {
      console::print("update end failed: %s", Update.errorString());
    }
  } else if (upload.status == UPLOAD_FILE_ABORTED) {
    Update.abort();
    console::print("firmware update aborted");
  }
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
  server.on("/update", HTTP_GET, handleUpdatePage);
  server.on("/update", HTTP_POST, handleUpdateDone, handleUpdateUpload);
  server.on("/api/message", HTTP_POST, handleMessage);
  server.on("/api/clear", HTTP_POST, handleClear);
  server.begin();
}

void handleClient() {
  server.handleClient();
}

}  // namespace web
