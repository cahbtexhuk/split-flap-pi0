#include "net.h"

#include <ESPmDNS.h>

#include "console.h"
#include "settings.h"

namespace net {

void startMdns() {
  MDNS.end();
  if (MDNS.begin(settings::get().hostname)) {
    MDNS.addService("http", "tcp", 80);
    console::print("mdns: http://%s.local", settings::get().hostname);
  } else {
    console::print("mdns start failed");
  }
}

}  // namespace net
