"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    // Get screen capture source IDs from the main process
    getScreenSources: () => electron_1.ipcRenderer.invoke('screen:get-sources'),
    // Overlay window visibility
    showOverlay: () => { electron_1.ipcRenderer.send('overlay:show'); },
    hideOverlay: () => { electron_1.ipcRenderer.send('overlay:hide'); },
    // Main renderer → main process → overlay renderer
    sendOverlayUpdate: (data) => {
        electron_1.ipcRenderer.send('overlay:update', data);
    },
    // Overlay renderer: subscribe to guidance updates forwarded by main process
    onOverlayUpdate: (cb) => {
        const listener = (_, data) => cb(data);
        electron_1.ipcRenderer.on('overlay:update', listener);
        return () => electron_1.ipcRenderer.removeListener('overlay:update', listener);
    },
    // Allow the main widget window to pass mouse events through transparent areas
    setIgnoreMouseEvents: (ignore) => {
        electron_1.ipcRenderer.send('main:set-ignore-mouse-events', ignore);
    },
});
