import { app, BrowserWindow, desktopCapturer, ipcMain, screen } from 'electron'
import path from 'path'

const isDev = process.env.NODE_ENV === 'development'

let mainWindow: BrowserWindow | null = null
let overlayWindow: BrowserWindow | null = null

function createMainWindow(): void {
  const { width, height } = screen.getPrimaryDisplay().bounds
  const winWidth = 380

  mainWindow = new BrowserWindow({
    x: width - winWidth,
    y: 0,
    width: winWidth,
    height,
    transparent: true,
    frame: false,
    hasShadow: false,
    skipTaskbar: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Sit above normal windows but below the guidance overlay ('screen-saver' level)
  mainWindow.setAlwaysOnTop(true, 'floating')
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  // Start click-through; renderer will disable it when mouse is over interactive content
  mainWindow.setIgnoreMouseEvents(true, { forward: true })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'))
  }
}

function createOverlayWindow(): void {
  const { width, height } = screen.getPrimaryDisplay().bounds

  overlayWindow = new BrowserWindow({
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
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Must be called after construction, not via constructor option, for the
  // 'screen-saver' level to take effect on macOS.
  overlayWindow.setAlwaysOnTop(true, 'screen-saver')
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  overlayWindow.setIgnoreMouseEvents(true, { forward: true })

  if (isDev) {
    overlayWindow.loadURL('http://localhost:5173/overlay.html')
  } else {
    overlayWindow.loadFile(path.join(__dirname, '../../dist/overlay.html'))
  }
}

app.whenReady().then(() => {
  createMainWindow()
  createOverlayWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// ── IPC Handlers ────────────────────────────────────────────────────────────

// Return available screen sources so renderer can create a capture stream
ipcMain.handle('screen:get-sources', async () => {
  const sources = await desktopCapturer.getSources({ types: ['screen'] })
  return sources.map(s => ({ id: s.id, name: s.name }))
})

// Show / hide the overlay window
ipcMain.on('overlay:show', () => overlayWindow?.show())
ipcMain.on('overlay:hide', () => overlayWindow?.hide())

// Forward guidance data from main renderer → overlay renderer
ipcMain.on('overlay:update', (_event, data: unknown) => {
  overlayWindow?.webContents.send('overlay:update', data)
})

// Toggle click-through on the main widget window
// Renderer calls this when the mouse enters/leaves interactive content
ipcMain.on('main:set-ignore-mouse-events', (_event, ignore: boolean) => {
  mainWindow?.setIgnoreMouseEvents(ignore, { forward: true })
})
