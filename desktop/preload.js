const { contextBridge } = require("electron");

// Lets the web UI know it runs inside the macOS app, where purchases go through RevenueCat.
contextBridge.exposeInMainWorld("MEETSPOT_PLATFORM", "macos");
