import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { GuidanceResponse, HintRegion } from '../types'

interface Props {
  response: GuidanceResponse
  stream: MediaStream
}

// CSS position for the instruction card per hint region
const CARD_STYLE: Record<HintRegion, React.CSSProperties> = {
  top_left:     { top: '16px',    left: '16px' },
  top_right:    { top: '16px',    right: '16px' },
  bottom_left:  { bottom: '16px', left: '16px' },
  bottom_right: { bottom: '16px', right: '16px' },
  center:       { top: '50%', left: '50%', transform: 'translate(-50%,-50%)' },
}

// Normalized anchor within the content area for the pulsing dot
const REGION_ANCHOR: Record<HintRegion, { nx: number; ny: number }> = {
  top_left:     { nx: 0.05, ny: 0.05 },
  top_right:    { nx: 0.95, ny: 0.05 },
  bottom_left:  { nx: 0.05, ny: 0.95 },
  bottom_right: { nx: 0.95, ny: 0.95 },
  center:       { nx: 0.50, ny: 0.50 },
}

export default function GuidanceOverlay({ response, stream }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [videoDims, setVideoDims] = useState({ w: 0, h: 0 })
  const [winSize, setWinSize] = useState({ w: window.innerWidth, h: window.innerHeight })

  // Attach the stream to the visible <video> element
  useEffect(() => {
    const v = videoRef.current
    if (v) {
      v.srcObject = stream
      v.play().catch(() => {})
    }
  }, [stream])

  // Keep window size in sync for coordinate math
  useEffect(() => {
    const onResize = () => setWinSize({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Compute the actual rendered content rect inside the <video> (object-fit: contain)
  // so bbox_norm coordinates map to the right pixels.
  const bounds = useMemo(() => {
    const { w: vw, h: vh } = videoDims
    const { w: ww, h: wh } = winSize
    if (!vw || !vh) return null
    const va = vw / vh
    const wa = ww / wh
    let rW: number, rH: number, oX: number, oY: number
    if (va > wa) { rW = ww; rH = ww / va; oX = 0;           oY = (wh - rH) / 2 }
    else         { rH = wh; rW = wh * va; oX = (ww - rW) / 2; oY = 0 }
    return { rW, rH, oX, oY }
  }, [videoDims, winSize])

  const { status, next_instruction, ui_target } = response
  const isOffTrack = status === 'off_track'
  const bbox = ui_target?.bbox_norm          // [x1, y1, x2, y2] normalized 0–1
  const hintRegion = ui_target?.hint_region ?? 'bottom_right'
  const color = isOffTrack ? '#f97316' : '#6366f1'
  const { w: ww, h: wh } = winSize

  // Bounding box in screen pixels (mapped into the rendered video content area)
  const bboxPx = bounds && bbox ? {
    x:  bounds.oX + bbox[0] * bounds.rW,
    y:  bounds.oY + bbox[1] * bounds.rH,
    w:  (bbox[2] - bbox[0]) * bounds.rW,
    h:  (bbox[3] - bbox[1]) * bounds.rH,
    cx: bounds.oX + ((bbox[0] + bbox[2]) / 2) * bounds.rW,
    cy: bounds.oY + ((bbox[1] + bbox[3]) / 2) * bounds.rH,
  } : null

  // Approximate pixel anchor for the call-out line start (near card edge)
  const cardLineAnchor: Record<HintRegion, { x: number; y: number }> = {
    top_left:     { x: 240,      y: 50 },
    top_right:    { x: ww - 240, y: 50 },
    bottom_left:  { x: 240,      y: wh - 50 },
    bottom_right: { x: ww - 240, y: wh - 50 },
    center:       { x: ww / 2,   y: wh / 2 },
  }
  const lineStart = cardLineAnchor[hintRegion]

  // Pulsing dot position (when no bbox)
  const dotPx = bounds
    ? {
        x: bounds.oX + REGION_ANCHOR[hintRegion].nx * bounds.rW,
        y: bounds.oY + REGION_ANCHOR[hintRegion].ny * bounds.rH,
      }
    : { x: ww * 0.9, y: wh * 0.9 }

  return (
    <div className="fixed inset-0 z-[9999] pointer-events-none">

      {/* ── Live screen capture video (fills viewport, letterboxed) ── */}
      <video
        ref={videoRef}
        className="absolute inset-0 w-full h-full"
        style={{ objectFit: 'contain', background: '#000' }}
        muted
        autoPlay
        onLoadedMetadata={() => {
          const v = videoRef.current!
          setVideoDims({ w: v.videoWidth, h: v.videoHeight })
        }}
      />

      {/* ── SVG annotation layer (pixel coordinates matching video content) ── */}
      <svg
        className="absolute inset-0"
        style={{ width: ww, height: wh }}
        viewBox={`0 0 ${ww} ${wh}`}
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

        {/* Dashed call-out line: instruction card → bbox center */}
        {bboxPx && (
          <motion.line
            x1={lineStart.x} y1={lineStart.y}
            x2={bboxPx.cx}   y2={bboxPx.cy}
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
          className={`absolute w-56 rounded-xl p-3 shadow-2xl text-sm bg-white ${
            isOffTrack ? 'border-2 border-orange-400' : 'border-2 border-indigo-400'
          }`}
          style={CARD_STYLE[hintRegion]}
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.88 }}
          transition={{ duration: 0.2 }}
        >
          {isOffTrack && (
            <p className="text-orange-500 font-semibold text-xs mb-1">⚠ Wrong page / view</p>
          )}
          <p className="text-gray-800 leading-snug">{next_instruction}</p>
          {ui_target?.target_text && (
            <p className="text-indigo-500 text-xs mt-2 font-medium">→ {ui_target.target_text}</p>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
