#pragma once

#include <Arduino.h>

namespace display {

struct SendResult {
  uint8_t sent;
  uint8_t failed;
  uint8_t speed;
};

void begin();
// requestedSpeed <= 0 or above MAX_ROTATION_SPEED falls back to the configured default speed.
SendResult sendMessage(const String& message, long requestedSpeed);
SendResult clear();
void scan();

}  // namespace display
