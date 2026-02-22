import { contextBridge, ipcRenderer } from 'electron'
import type { GuidanceResponse } from '../src/types'

contextBridge.exposeInMainWorld('electronAPI', {
  // Get screen capture source IDs from the main process
  getScreenSources: (): Promise<Array<{ id: string; name: string }>> =>
    ipcRenderer.invoke('screen:get-sources'),

  // Overlay window visibility
  showOverlay: (): void => { ipcRenderer.send('overlay:show') },
  hideOverlay: (): void => { ipcRenderer.send('overlay:hide') },

  // Main renderer → main process → overlay renderer
  sendOverlayUpdate: (data: GuidanceResponse): void => {
    ipcRenderer.send('overlay:update', data)
  },

  // Overlay renderer: subscribe to guidance updates forwarded by main process
  onOverlayUpdate: (cb: (data: GuidanceResponse) => void): (() => void) => {
    const listener = (_: Electron.IpcRendererEvent, data: GuidanceResponse) => cb(data)
    ipcRenderer.on('overlay:update', listener)
    return () => ipcRenderer.removeListener('overlay:update', listener)
  },

  // Allow the main widget window to pass mouse events through transparent areas
  setIgnoreMouseEvents: (ignore: boolean): void => {
    ipcRenderer.send('main:set-ignore-mouse-events', ignore)
  },

  // Move the main window by a pixel delta (renderer-driven drag)
  moveWindow: (dx: number, dy: number): void => {
    ipcRenderer.send('main:move-window', dx, dy)
  },

  // Resize the window to (width × height), anchored to the bottom-right corner
  resizeWindow: (width: number, height: number): void => {
    ipcRenderer.send('main:resize-window', width, height)
  },
})
