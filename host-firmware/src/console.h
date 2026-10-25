#pragma once

#include <Arduino.h>

#ifndef ENABLE_SERIAL_LOG
#define ENABLE_SERIAL_LOG 0
#endif

namespace console {

void begin();
void print(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
String dump();

}  // namespace console
