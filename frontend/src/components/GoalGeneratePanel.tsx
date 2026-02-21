import { useState } from 'react'
import { generatePlan } from '../services/api'
import type { Plan } from '../types'

interface Props {
  onPlanConfirmed: (plan: Plan) => void
}

export default function GoalGeneratePanel({ onPlanConfirmed }: Props) {
  const [goal, setGoal] = useState('')
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate() {
    if (!goal.trim()) return
    setLoading(true)
    setError(null)
    try {
      const p = await generatePlan(goal.trim())
      setPlan(p)
    } catch {
      setError('Failed to generate plan. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 flex flex-col gap-3">
      <h2 className="font-semibold text-gray-800 text-sm">What's your goal?</h2>

      <textarea
        className="w-full border border-gray-300 rounded-lg p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
        rows={3}
        placeholder="e.g. Create a GitHub repository"
        value={goal}
        onChange={e => setGoal(e.target.value)}
        disabled={loading || !!plan}
      />

      {!plan && (
        <button
          onClick={handleGenerate}
          disabled={loading || !goal.trim()}
          className="bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating…' : 'Generate Plan'}
        </button>
      )}

      {error && <p className="text-red-500 text-xs">{error}</p>}

      {plan && (
        <>
          {/* Plan preview */}
          <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700 flex flex-col gap-2 max-h-52 overflow-y-auto">
            {plan.assumptions.length > 0 && (
              <div>
                <p className="font-medium text-gray-500 mb-1">Assumptions</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {plan.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}
            <div>
              <p className="font-medium text-gray-500 mb-1">Steps</p>
              <ol className="list-decimal list-inside space-y-1">
                {plan.steps.map(step => (
                  <li key={step.id}>
                    <span className="font-medium">{step.title}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => setPlan(null)}
              className="flex-1 border border-gray-300 text-gray-600 rounded-lg py-2 text-sm hover:bg-gray-50 transition-colors"
            >
              Regenerate
            </button>
            <button
              onClick={() => onPlanConfirmed(plan)}
              className="flex-1 bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              Confirm
            </button>
          </div>
        </>
      )}
    </div>
  )
}
