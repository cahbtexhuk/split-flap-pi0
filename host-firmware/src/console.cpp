#include "console.h"

#include <stdarg.h>

namespace {

constexpr size_t kMaxLines = 100;
constexpr size_t kLineLen = 96;

char lines[kMaxLines][kLineLen];
size_t head = 0;
size_t count = 0;

}  // namespace

namespace console {

void begin() {
#if ENABLE_SERIAL_LOG
  Serial.begin(115200);
#endif
}

void print(const char* fmt, ...) {
  char msg[kLineLen - 12];
  va_list args;
  va_start(args, fmt);
  vsnprintf(msg, sizeof(msg), fmt, args);
  va_end(args);

  const unsigned long s = millis() / 1000;
  snprintf(lines[head], kLineLen, "[%02lu:%02lu:%02lu] %s", s / 3600, (s / 60) % 60, s % 60, msg);

#if ENABLE_SERIAL_LOG
  Serial.println(lines[head]);
#endif

  head = (head + 1) % kMaxLines;
  if (count < kMaxLines) {
    count++;
  }
}

String dump() {
  String out;
  out.reserve(count * 40);
  const size_t start = (head + kMaxLines - count) % kMaxLines;
  for (size_t i = 0; i < count; i++) {
    out += lines[(start + i) % kMaxLines];
    out += '\n';
  }
  return out;
}

}  // namespace console
