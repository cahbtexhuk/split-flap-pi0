#pragma once

namespace net {

// (Re)registers <hostname>.local and the http service; safe to call repeatedly.
void startMdns();

}  // namespace net
