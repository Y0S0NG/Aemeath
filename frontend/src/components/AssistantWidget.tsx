import { useEffect, useRef, useState } from 'react'
import type { Plan } from '../types'
import GoalGeneratePanel from './GoalGeneratePanel'
import PlanTrackPanel from './PlanTrackPanel'

type WidgetMode = 'goal' | 'plan'

// How many pixels the mouse must move before a mousedown becomes a drag
const DRAG_THRESHOLD = 5
// Button: w-14 h-14 = 56 px; bottom-6 right-6 = 24 px margin → 80 × 80 window
const COLLAPSED_W = 136
const COLLAPSED_H = 136
// Panel: right-6 = 24 px margin on right and bottom
const PANEL_MARGIN = 24

const CUSTOM_ICON_SRC = '/icons/icon.svg'

function ChatIcon({ size }: { size: 'sm' | 'md' }) {
  const [error, setError] = useState(false)
  const cls = size === 'md' ? 'w-28 h-28' : 'w-4 h-4'
  if (error) return <span className={size === 'md' ? 'text-2xl' : 'text-base'}>🧭</span>
  return (
    <img
      src={CUSTOM_ICON_SRC}
      alt="icon"
      draggable={false}
      className={`${cls} object-contain pointer-events-none`}
      onError={() => setError(true)}
    />
  )
}

export default function AssistantWidget() {
  const [isOpen, setIsOpen]   = useState(false)
  const [mode, setMode]       = useState<WidgetMode>('goal')
  const [plan, setPlan]       = useState<Plan | null>(null)
  const panelRef              = useRef<HTMLDivElement>(null)
  const drag                  = useRef({ active: false, startX: 0, startY: 0, prevX: 0, prevY: 0 })

  // ── Dynamic window sizing ────────────────────────────────────────────────
  // Whenever the panel opens / closes / changes content, resize the Electron
  // window to match the visible widget area exactly, so no transparent region
  // blocks clicks to the apps beneath.
  useEffect(() => {
    if (!isOpen) {
      window.electronAPI.resizeWindow(COLLAPSED_W, COLLAPSED_H)
      return
    }

    const panel = panelRef.current
    if (!panel) return

    const observer = new ResizeObserver(() => {
      const { width, height } = panel.getBoundingClientRect()
      window.electronAPI.resizeWindow(
        Math.ceil(width)  + PANEL_MARGIN,
        Math.ceil(height) + PANEL_MARGIN,
      )
    })
    observer.observe(panel)
    return () => observer.disconnect()
  }, [isOpen])

  // ── Event handlers ───────────────────────────────────────────────────────
  function handlePlanConfirmed(p: Plan) { setPlan(p); setMode('plan') }
  function handleReset()                { setMode('goal'); setPlan(null) }

  // Drag-or-click handler on the 🧭 button.
  // If the mouse moves ≥ DRAG_THRESHOLD px → drag the window via IPC.
  // If it barely moves → treat as a tap and toggle the panel.
  function handleButtonMouseDown(e: React.MouseEvent) {
    const state = drag.current
    state.active = false
    state.startX = state.prevX = e.screenX
    state.startY = state.prevY = e.screenY

    function onMouseMove(ev: MouseEvent) {
      const movedX = Math.abs(ev.screenX - state.startX)
      const movedY = Math.abs(ev.screenY - state.startY)
      if (!state.active && (movedX > DRAG_THRESHOLD || movedY > DRAG_THRESHOLD)) {
        state.active = true
      }
      if (state.active) {
        window.electronAPI.moveWindow(ev.screenX - state.prevX, ev.screenY - state.prevY)
        state.prevX = ev.screenX
        state.prevY = ev.screenY
      }
    }

    function onMouseUp() {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      if (!state.active) setIsOpen(o => !o)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <>
      {/* ── Collapsed: just the 🧭 button ── */}
      {!isOpen && (
        <button
          onMouseDown={handleButtonMouseDown}
          className="fixed bottom-6 right-6 z-50 w-28 h-28 flex items-center justify-center cursor-grab active:cursor-grabbing select-none"
          aria-label="Open assistant"
        >
          <ChatIcon size="md" />
        </button>
      )}

      {/* ── Expanded: panel only, no button ── */}
      {isOpen && (
        <div
          ref={panelRef}
          className="fixed bottom-6 right-6 z-50 w-80 bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col"
        >
          {/* Header — drag to move window */}
          <div className="drag-handle flex items-center justify-between px-4 py-2.5 border-b border-gray-100 bg-gray-50 rounded-t-2xl select-none">
            <div className="flex items-center gap-2">
              <ChatIcon size="sm" />
              <span className="text-xs font-medium text-gray-500">Aemeath</span>
            </div>
            <button
              className="no-drag text-gray-400 hover:text-gray-600 text-xl leading-none pb-0.5"
              onClick={() => setIsOpen(false)}
              aria-label="Close"
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="no-drag">
            {mode === 'goal' ? (
              <GoalGeneratePanel onPlanConfirmed={handlePlanConfirmed} />
            ) : (
              <PlanTrackPanel plan={plan!} onReset={handleReset} />
            )}
          </div>
        </div>
      )}
    </>
  )
}
