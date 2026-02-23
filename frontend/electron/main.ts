import { app, BrowserWindow, desktopCapturer, ipcMain, screen } from 'electron'
import path from 'path'

const isDev = process.env.NODE_ENV === 'development'

let mainWindow: BrowserWindow | null = null
let overlayWindow: BrowserWindow | null = null

function createMainWindow(): void {
  // Use workArea so the window is sized/placed within the menu-bar + dock margins
  const { x: waX, y: waY, width: waWidth, height: waHeight } =
    screen.getPrimaryDisplay().workArea
  // Start at button size; React will call 'main:resize-window' once it renders
  const winWidth  = 80
  const winHeight = 80

  mainWindow = new BrowserWindow({
    x: waX + waWidth  - winWidth,           // flush with right edge of work area
    y: waY + waHeight - winHeight,          // flush with bottom edge of work area
    width: winWidth,
    height: winHeight,
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

  // Exclude the panel from screen captures so OCR never picks up its own text.
  // On macOS this sets NSWindowSharingNone; on Windows it uses SetWindowDisplayAffinity.
  mainWindow.setContentProtection(true)

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

// Move the main window by a pixel delta (used for custom button drag)
ipcMain.on('main:move-window', (_event, dx: number, dy: number) => {
  if (!mainWindow) return
  const [x, y] = mainWindow.getPosition()
  mainWindow.setPosition(Math.round(x + dx), Math.round(y + dy))
})

// Resize the main window while keeping its bottom-right corner fixed.
// Called by the renderer whenever the widget's content size changes.
ipcMain.on('main:resize-window', (_event, width: number, height: number) => {
  if (!mainWindow) return
  const [x, y] = mainWindow.getPosition()
  const [oldW, oldH] = mainWindow.getSize()
  mainWindow.setBounds(
    { x: x + oldW - width, y: y + oldH - height, width, height },
    false, // no macOS animation
  )
})
