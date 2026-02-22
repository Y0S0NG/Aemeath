"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path_1 = __importDefault(require("path"));
const isDev = process.env.NODE_ENV === 'development';
let mainWindow = null;
let overlayWindow = null;
function createMainWindow() {
    const { width, height } = electron_1.screen.getPrimaryDisplay().bounds;
    const winWidth = 380;
    mainWindow = new electron_1.BrowserWindow({
        x: width - winWidth,
        y: 0,
        width: winWidth,
        height,
        transparent: true,
        frame: false,
        hasShadow: false,
        skipTaskbar: false,
        webPreferences: {
            preload: path_1.default.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    // Sit above normal windows but below the guidance overlay ('screen-saver' level)
    mainWindow.setAlwaysOnTop(true, 'floating');
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    // Start click-through; renderer will disable it when mouse is over interactive content
    mainWindow.setIgnoreMouseEvents(true, { forward: true });
    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
    }
    else {
        mainWindow.loadFile(path_1.default.join(__dirname, '../../dist/index.html'));
    }
}
function createOverlayWindow() {
    const { width, height } = electron_1.screen.getPrimaryDisplay().bounds;
    overlayWindow = new electron_1.BrowserWindow({
        x: 0,
        y: 0,
        width,
        height,
        transparent: true,
        frame: false,
        hasShadow: false,
        skipTaskbar: true,
        focusable: false,
        backgroundColor: '#00000000',
        show: false, // hidden until guidance starts
        webPreferences: {
            preload: path_1.default.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    // Must be called after construction, not via constructor option, for the
    // 'screen-saver' level to take effect on macOS.
    overlayWindow.setAlwaysOnTop(true, 'screen-saver');
    overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    overlayWindow.setIgnoreMouseEvents(true, { forward: true });
    if (isDev) {
        overlayWindow.loadURL('http://localhost:5173/overlay.html');
    }
    else {
        overlayWindow.loadFile(path_1.default.join(__dirname, '../../dist/overlay.html'));
    }
}
electron_1.app.whenReady().then(() => {
    createMainWindow();
    createOverlayWindow();
});
electron_1.app.on('window-all-closed', () => {
    if (process.platform !== 'darwin')
        electron_1.app.quit();
});
// ── IPC Handlers ────────────────────────────────────────────────────────────
// Return available screen sources so renderer can create a capture stream
electron_1.ipcMain.handle('screen:get-sources', async () => {
    const sources = await electron_1.desktopCapturer.getSources({ types: ['screen'] });
    return sources.map(s => ({ id: s.id, name: s.name }));
});
// Show / hide the overlay window
electron_1.ipcMain.on('overlay:show', () => overlayWindow?.show());
electron_1.ipcMain.on('overlay:hide', () => overlayWindow?.hide());
// Forward guidance data from main renderer → overlay renderer
electron_1.ipcMain.on('overlay:update', (_event, data) => {
    overlayWindow?.webContents.send('overlay:update', data);
});
// Toggle click-through on the main widget window
// Renderer calls this when the mouse enters/leaves interactive content
electron_1.ipcMain.on('main:set-ignore-mouse-events', (_event, ignore) => {
    mainWindow?.setIgnoreMouseEvents(ignore, { forward: true });
});
