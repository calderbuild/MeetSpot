const { app, BrowserWindow, shell } = require("electron");
const path = require("path");

// Local server during development; set MEETSPOT_URL to point at the hosted build.
const MEETSPOT_URL = process.env.MEETSPOT_URL || "http://127.0.0.1:8000/public/meetspot_finder.html";

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "MeetSpot",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
    },
  });

  // Keep MeetSpot inside the app window; send other sites to the default browser.
  const appOrigin = new URL(MEETSPOT_URL).origin;
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (new URL(url).origin === appOrigin) return { action: "allow" };
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.loadURL(MEETSPOT_URL);
}

app.setName("MeetSpot");
app.whenReady().then(() => {
  // `npm start` runs inside the stock Electron bundle; the packaged app gets this icon from icon.icns
  if (app.dock) app.dock.setIcon(path.join(__dirname, "build", "icon.png"));
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
