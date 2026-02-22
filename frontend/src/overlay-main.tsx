import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { motion } from 'framer-motion'
import './index.css'
import GuidanceOverlay from './components/GuidanceOverlay'
import type { GuidanceResponse } from './types'

function OverlayApp() {
  const [response, setResponse] = useState<GuidanceResponse | null>(null)

  useEffect(() => {
    const cleanup = window.electronAPI.onOverlayUpdate(setResponse)
    return cleanup
  }, [])

  const isOffTrack = response?.status === 'off_track'
  const borderColor = isOffTrack ? '#f97316' : '#6366f1'

  return (
    <>
      {/* Glowing screen border — visible as soon as monitoring starts */}
      <motion.div
        className="fixed inset-0 pointer-events-none"
        style={{
          boxShadow: `inset 0 0 0 3px ${borderColor}, inset 0 0 48px ${borderColor}55`,
        }}
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      />

      {response && <GuidanceOverlay response={response} />}
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <OverlayApp />
  </React.StrictMode>,
)
