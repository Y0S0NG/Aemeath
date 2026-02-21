# Frontend Implementation Guide

## 1. Components

### Assistant Widget
- Floating avatar button (always visible)
- Click to open/close the side panel
- Panel shows Goal Generate Panel first; switches to Plan Track Panel after plan is confirmed

### Goal Generate Panel
- Input block: user types their goal
- Generate Plan button: calls POST /plan/generate
- Plan Display Block: shows the returned structured plan (goal, assumptions, step list)
- Confirm Plan button: transitions panel to Plan Track Panel

### Plan Track Panel
- Step List View: displays all steps from the plan
- Highlights the current step (driven by current_step_id from the backend)
- Start Guidance button: requests screen share and begins the capture loop
- Stop Guidance button: stops the loop and releases the screen share stream
- Interval Setting: user-configurable screenshot polling interval (default: 5s)

### Guidance Overlay
A separate full-screen layer rendered on top of everything during guidance mode.

#### On-track (bbox_norm present):
- Glowing bounding box rectangle drawn at the target element position
- Call-out pointer line from the instruction card to the center of the bounding box
- Instruction card showing next_instruction text
- Framer Motion: pulse animation on the bounding box, fade-in/out on the card

#### Fallback (no bbox_norm — off_track or region-only hint):
- Pulsing dot anchored to the hint_region corner (top_left / top_right / bottom_left / bottom_right / center)
- Instruction card shown near that corner

#### Off-track styling:
- Instruction card gets an orange/red warning border
- Card displays an explicit "Wrong page/view" label above the next_instruction text

---

## 2. Screen Capture

### Stream Acquisition
- Triggered by: Start Guidance button click
- Calls: `navigator.mediaDevices.getDisplayMedia({ video: true })`
- Loop begins immediately after the user grants screen share permission (no preview step)

### Capture Loop
```
every <interval> seconds:
  1. Draw current video frame to an off-screen canvas
  2. Extract frame as base64 PNG (canvas.toDataURL → strip header)
  3. POST /guidance/analyze with { plan, current_step_id, screenshot_b64 }
  4. Receive GuidanceResponse → update overlay and step highlight
```

### Step Auto-advance
- current_step_id is driven by the backend response
- When response.step_done === true:
  - Advance to the next step in plan.steps[] (by index)
  - Update the highlighted step in Plan Track Panel
  - Next capture loop iteration sends the new current_step_id
- When all steps are done: stop the loop, show a completion message

---

## 3. Overlay Logic

```
if response.ui_target.bbox_norm exists:
  - Convert [x1, y1, x2, y2] (normalized 0–1) to pixel coords using screen dimensions
  - Draw glowing rectangle at those pixel coords
  - Draw call-out pointer line from instruction card to rectangle center
else:
  - Anchor a pulsing dot to hint_region corner
  - Show instruction card near that corner

if response.status === "off_track":
  - Add warning border (orange/red) to instruction card
  - Prepend "Wrong page — " label to the instruction text

Animations (Framer Motion):
  - Bounding box / dot: pulse animation
  - Instruction card: fade-in on appear, fade-out on dismiss
```
