import { AnimatePresence, motion } from 'framer-motion'
import type { GuidanceResponse } from '../types'

interface Props {
  response: GuidanceResponse
}

export default function GuidanceOverlay({ response }: Props) {
  // Overlay window covers the full primary display — use screen dimensions directly
  const sw = window.screen.width
  const sh = window.screen.height

  const { status, next_instruction, ui_target } = response
  const isOffTrack = status === 'off_track'
  const bbox = ui_target?.bbox_norm          // [x1, y1, x2, y2] normalized 0–1
  const color = isOffTrack ? '#f97316' : '#6366f1'

  // bbox_norm → absolute screen pixels
  const bboxPx = bbox ? {
    x:  bbox[0] * sw,
    y:  bbox[1] * sh,
    w:  (bbox[2] - bbox[0]) * sw,
    h:  (bbox[3] - bbox[1]) * sh,
    cx: ((bbox[0] + bbox[2]) / 2) * sw,
    cy: ((bbox[1] + bbox[3]) / 2) * sh,
  } : null

  // Card dimensions (w-56 = 224px wide; height is dynamic but estimated for placement)
  const CARD_W = 224
  const CARD_H = 80
  const GAP    = 10   // px gap between card edge and bbox edge

  // Position the card just above or below the bbox, horizontally aligned with it.
  // Falls back to bottom-right corner when there is no bbox.
  const { cardStyle, lineStart, lineEnd } = (() => {
    if (!bboxPx) return {
      cardStyle: { bottom: '16px', right: '16px' } as React.CSSProperties,
      lineStart: { x: sw - 240, y: sh - 50 },
      lineEnd:   { x: sw / 2,   y: sh / 2 },
    }

    const spaceAbove = bboxPx.y
    const spaceBelow = sh - (bboxPx.y + bboxPx.h)
    const above = spaceAbove >= spaceBelow || spaceAbove >= CARD_H + GAP

    const top  = Math.max(8, above
      ? bboxPx.y - CARD_H - GAP
      : bboxPx.y + bboxPx.h + GAP)
    const left = Math.min(Math.max(bboxPx.x, 8), sw - CARD_W - 8)

    // Line: card edge facing bbox → nearest bbox edge centre
    const lx = left + CARD_W / 2
    const ly = above ? top + CARD_H : top

    return {
      cardStyle: { position: 'absolute', top, left } as React.CSSProperties,
      lineStart: { x: lx, y: ly },
      lineEnd:   { x: bboxPx.cx, y: above ? bboxPx.y : bboxPx.y + bboxPx.h },
    }
  })()

  // Pulsing dot position for the no-bbox fallback — screen centre
  const dotPx = { x: sw / 2, y: sh / 2 }

  return (
    <div className="fixed inset-0 z-[9999] pointer-events-none">

      {/* ── SVG annotation layer ── */}
      <svg
        className="absolute inset-0"
        style={{ width: sw, height: sh }}
        viewBox={`0 0 ${sw} ${sh}`}
      >
        {/* Glowing bounding box */}
        {bboxPx && (
          <motion.rect
            x={bboxPx.x} y={bboxPx.y} width={bboxPx.w} height={bboxPx.h}
            fill="none"
            stroke={color}
            strokeWidth={3}
            rx={6}
            style={{ filter: `drop-shadow(0 0 8px ${color})` }}
            animate={{ opacity: [1, 0.35, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}

        {/* Dashed call-out line: card edge → nearest bbox edge */}
        {bboxPx && (
          <motion.line
            x1={lineStart.x} y1={lineStart.y}
            x2={lineEnd.x}   y2={lineEnd.y}
            stroke={color} strokeWidth={2}
            strokeDasharray="8 5" strokeLinecap="round"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.65 }}
            transition={{ duration: 0.3 }}
          />
        )}

        {/* Pulsing dot — fallback when no bbox */}
        {!bboxPx && (
          <motion.circle
            cx={dotPx.x} cy={dotPx.y} r={10}
            fill={color}
            animate={{ r: [10, 18, 10], opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
      </svg>

      {/* ── Instruction card ── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={next_instruction}
          className={`absolute w-56 rounded-xl p-3 text-sm backdrop-blur-sm ${
            isOffTrack
              ? 'bg-orange-900/40 border border-orange-400/60'
              : 'bg-indigo-900/40 border border-indigo-400/60'
          }`}
          style={cardStyle}
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.88 }}
          transition={{ duration: 0.2 }}
        >
          {isOffTrack && (
            <p className="text-orange-300 font-semibold text-xs mb-1">⚠ Wrong page / view</p>
          )}
          <p className="text-white leading-snug drop-shadow">{next_instruction}</p>
          {ui_target?.target_text && (
            <p className="text-indigo-300 text-xs mt-2 font-medium">→ {ui_target.target_text}</p>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
