#include "display.h"

#include <Wire.h>

#include "console.h"
#include "settings.h"

#ifndef I2C_SDA_PIN
#define I2C_SDA_PIN 21
#endif
#ifndef I2C_SCL_PIN
#define I2C_SCL_PIN 22
#endif
#ifndef I2C_CLOCK_HZ
#define I2C_CLOCK_HZ 100000
#endif

namespace {

// Flap order from firmware/src/unit/Unit.cpp: " A-Z", 3 umlauts, "0-9", ":", ".", "-", "?", "!".
int flapIndex(const String& text, size_t& pos) {
  uint8_t c = text[pos++];

  if (c >= 0xC0) {
    if (c == 0xC3 && pos < text.length()) {
      const uint8_t next = text[pos++];
      if (next == 0x84 || next == 0xA4) return 27;
      if (next == 0x96 || next == 0xB6) return 28;
      if (next == 0x9C || next == 0xBC) return 29;
    }
    while (pos < text.length() && (static_cast<uint8_t>(text[pos]) & 0xC0) == 0x80) {
      pos++;
    }
    return 0;
  }

  if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
  if (c >= 'A' && c <= 'Z') return 1 + (c - 'A');
  if (c >= '0' && c <= '9') return 30 + (c - '0');
  switch (c) {
    case ':': return 40;
    case '.': return 41;
    case '-': return 42;
    case '?': return 43;
    case '!': return 44;
    default: return 0;
  }
}

uint8_t resolveSpeed(long requested) {
  if (requested >= 1 && requested <= MAX_ROTATION_SPEED) {
    return static_cast<uint8_t>(requested);
  }
  return settings::get().defaultSpeed;
}

bool writeUnit(uint8_t address, uint8_t flap, uint8_t speed) {
  Wire.beginTransmission(address);
  Wire.write(flap);
  Wire.write(speed);
  return Wire.endTransmission() == 0;
}

void appendAddress(String& list, uint8_t address) {
  char buf[8];
  snprintf(buf, sizeof(buf), " 0x%02x", address);
  list += buf;
}

}  // namespace

namespace display {

void begin() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, I2C_CLOCK_HZ);
  Wire.setTimeOut(50);
}

SendResult sendMessage(const String& message, long requestedSpeed) {
  const Settings& cfg = settings::get();
  SendResult result = {0, 0, resolveSpeed(requestedSpeed)};
  String failedList;

  size_t pos = 0;
  uint8_t unit = 0;
  while (pos < message.length() && unit < cfg.numSymbols) {
    const uint8_t address = settings::unitAddress(unit);
    if (writeUnit(address, flapIndex(message, pos), result.speed)) {
      result.sent++;
    } else {
      result.failed++;
      appendAddress(failedList, address);
    }
    unit++;
    delay(1);
  }

  console::print("message \"%.40s\" speed=%u sent=%u failed=%u", message.c_str(), result.speed, result.sent, result.failed);
  if (result.failed) {
    console::print("no ack from:%s", failedList.c_str());
  }
  return result;
}

SendResult clear() {
  const Settings& cfg = settings::get();
  SendResult result = {0, 0, cfg.defaultSpeed};
  String failedList;

  for (uint8_t unit = 0; unit < cfg.numSymbols; unit++) {
    const uint8_t address = settings::unitAddress(unit);
    if (writeUnit(address, 0, result.speed)) {
      result.sent++;
    } else {
      result.failed++;
      appendAddress(failedList, address);
    }
    delay(1);
  }

  console::print("clear display sent=%u failed=%u", result.sent, result.failed);
  if (result.failed) {
    console::print("no ack from:%s", failedList.c_str());
  }
  return result;
}

void scan() {
  const Settings& cfg = settings::get();
  uint8_t found = 0;
  String missing;

  for (uint8_t unit = 0; unit < cfg.numSymbols; unit++) {
    const uint8_t address = settings::unitAddress(unit);
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      found++;
    } else {
      appendAddress(missing, address);
    }
  }

  console::print("scan 0x%02x..0x%02x: found %u/%u", settings::unitAddress(0),
                 settings::unitAddress(cfg.numSymbols - 1), found, cfg.numSymbols);
  if (found < cfg.numSymbols) {
    console::print("missing:%s", missing.c_str());
  }
}

}  // namespace display
