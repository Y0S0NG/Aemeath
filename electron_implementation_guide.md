# 📦 Migration Guide  
## Converting Existing React Frontend into an Electron Desktop Application

Project: Goal-Driven Visual Copilot  
Objective: Wrap the existing React frontend into a desktop application that supports:
- Always-on-top overlay window
- Transparent click-through rendering
- Global screen capture
- Cross-app persistent assistant

This document provides structured implementation steps for an AI coding agent.


# 1. High-Level Goal

We currently have:
+ React (Vite) frontend
+ Python FastAPI backend

We want:
Electron Desktop App with:
+ Main Window (React UI)
+ Overlay Window (Transparent, Always-On-Top)
+ Screen Capture
+  ⬇️
+ Python Backend

We are NOT rewriting the frontend.

We are embedding it inside Electron.



# 2. Migration Strategy

We will:
1. Install Electron
2. Add Electron main process
3. Convert React app to load inside Electron window
4. Create overlay window
5. Enable screen capture
6. Establish IPC communication
7. Add build configuration

No React rewrite required.


# 3. Step-by-Step Migration Plan
## Step 1 — Install Electron

From project root:

```bash
npm install --save-dev electron electron-builder concurrently wait-on
```

## Step 2 — Project Structure Update

Modify structure to:
```
/project-root
 ├── /electron
 │     ├── main.ts
 │     ├── preload.ts
 │
 ├── /src        (existing React app)
 ├── package.json
 └── vite.config.ts
```
## Step 3 — Create Electron Main Process

Create:

/electron/main.ts

Responsibilities:
	•	Create main window
	•	Create overlay window
	•	Manage lifecycle
	•	Handle IPC

Core logic outline:
	1.	Wait for app ready
	2.	Create main window
	3.	Load React dev server (dev) or build output (prod)
	4.	Create overlay window
	5.	Set alwaysOnTop + transparent

Important Window Configurations:

Main Window:
	•	width/height normal
	•	frame: true

Overlay Window:
	•	transparent: true
	•	frame: false
	•	alwaysOnTop: true
	•	skipTaskbar: true
	•	focusable: false
	•	fullscreen: true
	•	backgroundColor: ‘#00000000’

This makes overlay float over everything.

## Step 4 — Preload Script
Create:

`/electron/preload.ts`

Purpose:
+ Expose safe IPC APIs to React frontend
+ Prevent direct Node access

Use:
`contextBridge.exposeInMainWorld(...)`


Expose functions like:
+ startScreenCapture()
+ stopOverlay()
+ sendOverlayUpdate(data)

## Step 5 - Update package.json
Add: 
```
"main": "electron/main.ts",
"scripts": {
  "dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
  "build": "vite build",
  "electron:build": "electron-builder"
}
```

# 4. Overlay Window Implementation
Overlay window is separate from main UI window.

It should:
	•	Be transparent
	•	Render React overlay component
	•	Ignore pointer events unless needed

To allow click-through:

Use:
`win.setIgnoreMouseEvents(true, { forward: true })`

To temporarily allow interaction:

Toggle ignoreMouseEvents off.

# 5. Screen Capture Implementation
In Electron, use:
`desktopCapturer.getSources()`

or

Use browser API inside renderer:
`navigator.mediaDevices.getDisplayMedia()`

Recommended for MVP:
Use getDisplayMedia in renderer.

Electron will allow full screen capture without browser restrictions.

# 6. IPC Communication Design
We need:

Main process <-> Renderer process communication.

Define channels:
+ “overlay:update”
+ “overlay:show”
+ “overlay:hide”
+ “screen:start”
+ “screen:stop”

Flow:
1. Renderer sends screenshot to backend
2. Backend returns guidance JSON
3. Renderer sends overlay data to main
4. Main forwards to overlay window
5. Overlay window updates highlight

# 7.  Overlay Rendering Strategy
In overlay React component:
+ Fullscreen div
+ pointer-events: none
+ Canvas layer for bounding box
+ Animated arrow
+ Tooltip container

Coordinates:
Use normalized bbox → multiply by screen width/height.

Add pulse animation via Framer Motion.

# 9. Production Build Configuration
Use electron-builder.

Add in package.json:
```
"build": {
  "appId": "com.aicopilot.app",
  "mac": {
    "category": "public.app-category.developer-tools"
  }
}
```
Then:
`npm run electron:build`

# 10. Backend Communication
Electron frontend will continue calling:
```
http://localhost:8000/generate-plan
http://localhost:8000/analyze-screen
```
No backend change required.

# 11. Migration Checklist
+ Electron installed
+ Main process created
+ Preload bridge created
+ Main window loads React
+ Overlay window implemented
+ Screen capture works
+ Overlay renders highlight
+ IPC communication stable
+ Build packaging works

