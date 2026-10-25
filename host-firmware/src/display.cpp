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
#define I2C_CLOCK_HZ 50000
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

constexpr uint8_t kChannelUnknown = 0xFF;
// TCA channel each unit answered on during the last scan, indexed by unit position.
uint8_t channelMap[kMaxUnits] = {kChannelUnknown, kChannelUnknown, kChannelUnknown, kChannelUnknown, kChannelUnknown,
                                 kChannelUnknown, kChannelUnknown, kChannelUnknown, kChannelUnknown, kChannelUnknown};

uint8_t enabledChannels(const Settings& cfg, uint8_t* out) {
  uint8_t count = 0;
  for (uint8_t ch = 0; ch < 8; ch++) {
    if (cfg.tcaChannels & (1 << ch)) {
      out[count++] = ch;
    }
  }
  return count;
}

bool selectChannel(const Settings& cfg, uint8_t channel) {
  Wire.beginTransmission(cfg.tcaAddress);
  Wire.write(static_cast<uint8_t>(1 << channel));
  return Wire.endTransmission() == 0;
}

// A zero-byte write would still fire the unit's onReceive(0) and corrupt its letter/speed, so read the status byte.
bool probeUnit(uint8_t address) {
  if (Wire.requestFrom(static_cast<uint16_t>(address), static_cast<size_t>(1), true) != 1) {
    return false;
  }
  Wire.read();
  return true;
}

// Units not seen by the last scan are spread evenly over the enabled channels.
uint8_t channelForUnit(const Settings& cfg, uint8_t unit, const uint8_t* channels, uint8_t channelCount) {
  const uint8_t mapped = channelMap[unit];
  if (mapped != kChannelUnknown && (cfg.tcaChannels & (1 << mapped))) {
    return mapped;
  }
  return channels[min<uint8_t>(channelCount - 1, unit * channelCount / cfg.numSymbols)];
}

void writeAll(const uint8_t* flaps, uint8_t count, display::SendResult& result, String& failedList) {
  const Settings& cfg = settings::get();

  if (!cfg.tcaEnabled) {
    for (uint8_t unit = 0; unit < count; unit++) {
      const uint8_t address = settings::unitAddress(unit);
      if (writeUnit(address, flaps[unit], result.speed)) {
        result.sent++;
      } else {
        result.failed++;
        appendAddress(failedList, address);
      }
      delay(1);
    }
    return;
  }

  uint8_t channels[8];
  const uint8_t channelCount = enabledChannels(cfg, channels);
  for (uint8_t c = 0; c < channelCount; c++) {
    bool tried = false;
    bool selected = false;
    for (uint8_t unit = 0; unit < count; unit++) {
      if (channelForUnit(cfg, unit, channels, channelCount) != channels[c]) continue;
      if (!tried) {
        selected = selectChannel(cfg, channels[c]);
        tried = true;
        if (!selected) {
          console::print("tca 0x%02x no ack selecting ch%u", cfg.tcaAddress, channels[c]);
        }
      }
      const uint8_t address = settings::unitAddress(unit);
      if (selected && writeUnit(address, flaps[unit], result.speed)) {
        result.sent++;
      } else {
        result.failed++;
        appendAddress(failedList, address);
      }
      delay(1);
    }
  }
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

  uint8_t flaps[kMaxUnits];
  uint8_t count = 0;
  size_t pos = 0;
  while (pos < message.length() && count < cfg.numSymbols) {
    flaps[count++] = flapIndex(message, pos);
  }
  writeAll(flaps, count, result, failedList);

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

  uint8_t flaps[kMaxUnits] = {};
  writeAll(flaps, cfg.numSymbols, result, failedList);

  console::print("clear display sent=%u failed=%u", result.sent, result.failed);
  if (result.failed) {
    console::print("no ack from:%s", failedList.c_str());
  }
  return result;
}

void scan() {
  const Settings& cfg = settings::get();
  bool seen[kMaxUnits] = {};
  for (uint8_t unit = 0; unit < kMaxUnits; unit++) {
    channelMap[unit] = kChannelUnknown;
  }

  if (cfg.tcaEnabled) {
    uint8_t channels[8];
    const uint8_t channelCount = enabledChannels(cfg, channels);
    for (uint8_t c = 0; c < channelCount; c++) {
      if (!selectChannel(cfg, channels[c])) {
        console::print("tca 0x%02x no ack selecting ch%u", cfg.tcaAddress, channels[c]);
        continue;
      }
      String onChannel;
      for (uint8_t unit = 0; unit < cfg.numSymbols; unit++) {
        if (!seen[unit] && probeUnit(settings::unitAddress(unit))) {
          seen[unit] = true;
          channelMap[unit] = channels[c];
          appendAddress(onChannel, settings::unitAddress(unit));
        }
      }
      console::print("ch%u:%s", channels[c], onChannel.length() ? onChannel.c_str() : " none");
    }
  } else {
    for (uint8_t unit = 0; unit < cfg.numSymbols; unit++) {
      seen[unit] = probeUnit(settings::unitAddress(unit));
    }
  }

  uint8_t found = 0;
  String missing;
  for (uint8_t unit = 0; unit < cfg.numSymbols; unit++) {
    if (seen[unit]) {
      found++;
    } else {
      appendAddress(missing, settings::unitAddress(unit));
    }
  }

  console::print("scan 0x%02x..0x%02x: found %u/%u", settings::unitAddress(0),
                 settings::unitAddress(cfg.numSymbols - 1), found, cfg.numSymbols);
  if (found < cfg.numSymbols) {
    console::print("missing:%s", missing.c_str());
  }
}

}  // namespace display
