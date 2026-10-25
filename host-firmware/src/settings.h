#pragma once

#include <Arduino.h>

#ifndef MAX_ROTATION_SPEED
#define MAX_ROTATION_SPEED 255
#endif
static_assert(MAX_ROTATION_SPEED >= 1 && MAX_ROTATION_SPEED <= 255, "speed is sent as a single byte");

constexpr uint8_t kMaxUnits = 10;
// Must match I2C_ADDRESS_BASE in firmware/src/unit/Unit.cpp; unit address = base + 4-bit switch value.
constexpr uint8_t kI2cAddressBase = 0x10;
constexpr uint8_t kMaxSwitchValue = 15;

struct Settings {
  uint8_t numSymbols;
  uint8_t defaultSpeed;
  uint8_t firstUnitAddress;  // switch value of the first unit, not the raw I2C address
  char hostname[32];
  bool tcaEnabled;
  uint8_t tcaAddress;
  uint8_t tcaChannels;  // bit n set = TCA9548A channel n is used
};

// Raw values as submitted by the settings form.
struct SettingsInput {
  long numSymbols;
  long defaultSpeed;
  long firstUnitAddress;
  String hostname;
  bool tcaEnabled;
  String tcaAddress;   // decimal or 0x-prefixed hex
  String tcaChannels;  // e.g. "0, 1"
};

namespace settings {

void load();
void apply(const SettingsInput& input);
const Settings& get();
uint8_t unitAddress(uint8_t index);
String channelsText();

}  // namespace settings
