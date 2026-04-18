// BIL extension — endpoint configuration.
//
// EDIT THIS FILE FOR YOUR NETWORK. The defaults assume a Synology NAS at
// 192.168.1.177 running BIL on port 8420 (with a localhost fallback for
// testing on the NAS itself). The background service worker iterates the
// list in order and uses the first endpoint that returns a 2xx response.
self.BIL_ENDPOINTS = [
  "http://192.168.1.177:8420/bil/web",
  "http://localhost:8420/bil/web",
];
