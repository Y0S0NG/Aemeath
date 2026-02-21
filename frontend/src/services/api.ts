import type { Plan, GuidanceResponse } from '../types'

const BASE_URL = 'http://127.0.0.1:8000'

export async function generatePlan(goal: string): Promise<Plan> {
  const res = await fetch(`${BASE_URL}/plan/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal }),
  })
  if (!res.ok) throw new Error(`Plan generation failed: ${res.status}`)
  return res.json() as Promise<Plan>
}

export async function analyzeScreenshot(
  plan: Plan,
  current_step_id: string,
  screenshot_b64: string,
): Promise<GuidanceResponse> {
  const res = await fetch(`${BASE_URL}/guidance/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan, current_step_id, screenshot_b64 }),
  })
  if (!res.ok) throw new Error(`Guidance analysis failed: ${res.status}`)
  return res.json() as Promise<GuidanceResponse>
}
