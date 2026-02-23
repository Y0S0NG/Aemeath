import { useState } from 'react'
import type { Plan } from '../types'
import { useScreenCapture, type CaptureMode } from '../hooks/useScreenCapture'

interface Props {
  plan: Plan
  onReset: () => void
}

export default function PlanTrackPanel({ plan, onReset }: Props) {
  const [intervalSecs, setIntervalSecs] = useState(5)
  const [mode, setMode] = useState<CaptureMode>('auto')

  const {
    isCapturing,
    isAnalyzing,
    isComplete,
    currentStepId,
    startCapture,
    stopCapture,
    captureAndAnalyze,
    advanceStep,
  } = useScreenCapture(plan, intervalSecs, mode)

  const currentIdx = plan.steps.findIndex(s => s.id === currentStepId)
  const isLastStep = currentIdx === plan.steps.length - 1

  return (
    <>
      <div className="p-4 flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800 text-sm truncate flex-1 mr-2">{plan.goal}</h2>
          <button
            onClick={onReset}
            className="text-xs text-gray-400 hover:text-gray-600 flex-shrink-0"
          >
            ↩ Reset
          </button>
        </div>

        {/* Step list */}
        <ol className="flex flex-col gap-1.5">
          {plan.steps.map((step, idx) => {
            const isCurrent = step.id === currentStepId
            const isDone = isComplete || (currentIdx > -1 && idx < currentIdx)

            return (
              <li
                key={step.id}
                className={`flex items-start gap-2 rounded-lg px-2 py-1.5 text-xs transition-colors ${
                  isCurrent ? 'bg-indigo-50 border border-indigo-200' : ''
                }`}
              >
                <span
                  className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                    isDone
                      ? 'bg-green-500 text-white'
                      : isCurrent
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {isDone ? '✓' : idx + 1}
                </span>
                <span
                  className={
                    isDone
                      ? 'text-gray-400 line-through'
                      : isCurrent
                        ? 'text-indigo-800 font-medium'
                        : 'text-gray-600'
                  }
                >
                  {step.title}
                </span>
              </li>
            )
          })}
        </ol>

        {/* Completion banner */}
        {isComplete && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-2 text-xs text-green-700 text-center font-medium">
            All steps complete! 🎉
          </div>
        )}

        {/* Mode toggle + interval slider — hidden while capturing */}
        {!isCapturing && !isComplete && (
          <div className="flex flex-col gap-2">
            {/* Auto / Manual toggle */}
            <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs font-medium">
              {(['auto', 'manual'] as CaptureMode[]).map(m => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex-1 py-1.5 capitalize transition-colors ${
                    mode === m
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>

            {/* Interval slider — auto mode only */}
            {mode === 'auto' && (
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className="flex-shrink-0">Interval</span>
                <input
                  type="range"
                  min={2}
                  max={15}
                  step={1}
                  value={intervalSecs}
                  onChange={e => setIntervalSecs(Number(e.target.value))}
                  className="flex-1 accent-indigo-600"
                />
                <span className="w-7 text-right">{intervalSecs}s</span>
              </div>
            )}
          </div>
        )}

        {/* Start / Stop + Analyze Now buttons */}
        {!isComplete && (
          <div className="flex gap-2">
            <button
              onClick={isCapturing ? stopCapture : startCapture}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors ${
                isCapturing
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              }`}
            >
              {isCapturing ? 'Stop' : 'Start Guidance'}
            </button>

            {/* Manual trigger — only shown when capturing in manual mode */}
            {isCapturing && mode === 'manual' && (
              <button
                onClick={captureAndAnalyze}
                disabled={isAnalyzing}
                className="flex-1 rounded-lg py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isAnalyzing ? 'Analyzing…' : 'Analyze Now'}
              </button>
            )}

            {/* Manual step advance — always visible while capturing */}
            {isCapturing && (
              <button
                onClick={advanceStep}
                disabled={isLastStep}
                title={isLastStep ? 'Already on last step' : 'Skip to next step'}
                className="rounded-lg py-2 px-3 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ↓
              </button>
            )}
          </div>
        )}
      </div>

    </>
  )
}
