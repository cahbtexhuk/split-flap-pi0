#include "settings.h"

#include <Preferences.h>

namespace {

constexpr const char* kNamespace = "splitflap";
constexpr const char* kDefaultHostname = "splitflap";

Settings current = {kMaxUnits, 8, 1, "splitflap", true, 0x70, 0x03};
Preferences prefs;

long clampLong(long value, long low, long high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}

String sanitizeHostname(const String& in) {
  String out;
  for (size_t i = 0; i < in.length() && out.length() < sizeof(Settings::hostname) - 1; i++) {
    const char c = tolower(in[i]);
    if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-') {
      out += c;
    }
  }
  while (out.startsWith("-")) out.remove(0, 1);
  while (out.endsWith("-")) out.remove(out.length() - 1);
  return out.length() ? out : String(kDefaultHostname);
}

uint8_t parseChannels(const String& text) {
  uint8_t mask = 0;
  for (size_t i = 0; i < text.length(); i++) {
    if (text[i] >= '0' && text[i] <= '7') {
      mask |= 1 << (text[i] - '0');
    }
  }
  return mask ? mask : 0x03;
}

Settings sanitize(long numSymbols, long defaultSpeed, long firstUnitAddress, const String& hostname,
                  bool tcaEnabled, long tcaAddress, uint8_t tcaChannels) {
  Settings s;
  s.firstUnitAddress = clampLong(firstUnitAddress, 0, kMaxSwitchValue);
  const long unitsLeftInAddressSpace = kMaxSwitchValue + 1 - s.firstUnitAddress;
  s.numSymbols = clampLong(numSymbols, 1, min<long>(kMaxUnits, unitsLeftInAddressSpace));
  s.defaultSpeed = clampLong(defaultSpeed, 1, MAX_ROTATION_SPEED);
  strlcpy(s.hostname, sanitizeHostname(hostname).c_str(), sizeof(s.hostname));
  s.tcaEnabled = tcaEnabled;
  s.tcaAddress = (tcaAddress >= 0x08 && tcaAddress <= 0x77) ? tcaAddress : 0x70;
  s.tcaChannels = tcaChannels ? tcaChannels : 0x03;
  return s;
}

}  // namespace

namespace settings {

void load() {
  prefs.begin(kNamespace, false);
  current = sanitize(prefs.getUChar("num", current.numSymbols),
                     prefs.getUChar("speed", current.defaultSpeed),
                     prefs.getUChar("first", current.firstUnitAddress),
                     prefs.getString("host", current.hostname),
                     prefs.getBool("tca", current.tcaEnabled),
                     prefs.getUChar("tcaaddr", current.tcaAddress),
                     prefs.getUChar("tcach", current.tcaChannels));
  prefs.end();
}

void apply(const SettingsInput& in) {
  current = sanitize(in.numSymbols, in.defaultSpeed, in.firstUnitAddress, in.hostname, in.tcaEnabled,
                     strtol(in.tcaAddress.c_str(), nullptr, 0), parseChannels(in.tcaChannels));
  prefs.begin(kNamespace, false);
  prefs.putUChar("num", current.numSymbols);
  prefs.putUChar("speed", current.defaultSpeed);
  prefs.putUChar("first", current.firstUnitAddress);
  prefs.putString("host", current.hostname);
  prefs.putBool("tca", current.tcaEnabled);
  prefs.putUChar("tcaaddr", current.tcaAddress);
  prefs.putUChar("tcach", current.tcaChannels);
  prefs.end();
}

String channelsText() {
  String text;
  for (uint8_t ch = 0; ch < 8; ch++) {
    if (current.tcaChannels & (1 << ch)) {
      if (text.length()) text += ", ";
      text += ch;
    }
  }
  return text;
}

const Settings& get() {
  return current;
}

uint8_t unitAddress(uint8_t index) {
  return kI2cAddressBase + current.firstUnitAddress + index;
}

}  // namespace settings
