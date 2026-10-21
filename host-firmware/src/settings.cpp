#include "settings.h"

#include <Preferences.h>

namespace {

constexpr const char* kNamespace = "splitflap";

Settings current = {kMaxUnits, 8, 1};
Preferences prefs;

long clampLong(long value, long low, long high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

Settings sanitize(long numSymbols, long defaultSpeed, long firstUnitAddress) {
  Settings s;
  s.firstUnitAddress = clampLong(firstUnitAddress, 0, kMaxSwitchValue);
  const long unitsLeftInAddressSpace = kMaxSwitchValue + 1 - s.firstUnitAddress;
  s.numSymbols = clampLong(numSymbols, 1, min<long>(kMaxUnits, unitsLeftInAddressSpace));
  s.defaultSpeed = clampLong(defaultSpeed, 1, MAX_ROTATION_SPEED);
  return s;
}

}  // namespace

namespace settings {

void load() {
  prefs.begin(kNamespace, false);
  current = sanitize(prefs.getUChar("num", current.numSymbols),
                     prefs.getUChar("speed", current.defaultSpeed),
                     prefs.getUChar("first", current.firstUnitAddress));
  prefs.end();
}

void apply(long numSymbols, long defaultSpeed, long firstUnitAddress) {
  current = sanitize(numSymbols, defaultSpeed, firstUnitAddress);
  prefs.begin(kNamespace, false);
  prefs.putUChar("num", current.numSymbols);
  prefs.putUChar("speed", current.defaultSpeed);
  prefs.putUChar("first", current.firstUnitAddress);
  prefs.end();
}

const Settings& get() {
  return current;
}

uint8_t unitAddress(uint8_t index) {
  return kI2cAddressBase + current.firstUnitAddress + index;
}

}  // namespace settings
