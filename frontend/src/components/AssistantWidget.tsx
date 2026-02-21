import { useState } from 'react'
import type { Plan } from '../types'
import GoalGeneratePanel from './GoalGeneratePanel'
import PlanTrackPanel from './PlanTrackPanel'

type WidgetMode = 'goal' | 'plan'

export default function AssistantWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<WidgetMode>('goal')
  const [plan, setPlan] = useState<Plan | null>(null)

  function handlePlanConfirmed(p: Plan) {
    setPlan(p)
    setMode('plan')
  }

  function handleReset() {
    setMode('goal')
    setPlan(null)
  }

  return (
    <>
      {/* Floating avatar button */}
      <button
        onClick={() => setIsOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg flex items-center justify-center text-2xl hover:bg-indigo-700 transition-colors"
        aria-label="Toggle assistant"
      >
        🧭
      </button>

      {/* Side panel */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-80 bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {mode === 'goal' ? (
            <GoalGeneratePanel onPlanConfirmed={handlePlanConfirmed} />
          ) : (
            <PlanTrackPanel plan={plan!} onReset={handleReset} />
          )}
        </div>
      )}
    </>
  )
}
