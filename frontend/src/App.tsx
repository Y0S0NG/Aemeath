import { useEffect } from 'react'
import AssistantWidget from './components/AssistantWidget'

export default function App() {
  // Dynamically enable/disable mouse click-through on transparent areas.
  // When the cursor is over the body or root (transparent background), let
  // events pass through to whatever is under the Electron window.
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const el = document.elementFromPoint(e.clientX, e.clientY)
      const isOverContent =
        el !== null &&
        el !== document.documentElement &&
        el !== document.body &&
        el !== document.getElementById('root')
      window.electronAPI.setIgnoreMouseEvents(!isOverContent)
    }
    document.addEventListener('mousemove', handleMouseMove)
    return () => document.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div className="w-full h-full">
      <AssistantWidget />
    </div>
  )
}
