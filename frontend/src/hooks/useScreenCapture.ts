import { useCallback, useRef, useState } from 'react'
import { analyzeScreenshot } from '../services/api'
import type { GuidanceResponse, Plan } from '../types'

export function useScreenCapture(plan: Plan | null, intervalSecs: number) {
  const [isCapturing, setIsCapturing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [currentStepId, setCurrentStepId] = useState<string | null>(null)
  const [guidanceResponse, setGuidanceResponse] = useState<GuidanceResponse | null>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)

  const streamRef = useRef<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Mutable refs so interval callback always reads latest values without needing re-creation
  const stepIdRef = useRef<string | null>(null)
  const planRef = useRef<Plan | null>(plan)
  planRef.current = plan

  const stopCapture = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    videoRef.current = null
    setStream(null)
    setIsCapturing(false)
    setGuidanceResponse(null)
  }, [])

  const captureAndAnalyze = useCallback(async () => {
    const p = planRef.current
    const video = videoRef.current
    const canvas = canvasRef.current
    const stepId = stepIdRef.current
    if (!p || !video || !canvas || !stepId) return

    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0)

    const b64 = canvas.toDataURL('image/png').split(',')[1]

    try {
      const response = await analyzeScreenshot(p, stepId, b64)
      setGuidanceResponse(response)

      const stepIndex = p.steps.findIndex(s => s.id === response.current_step_id)
      stepIdRef.current = response.current_step_id
      setCurrentStepId(response.current_step_id)

      if (response.step_done && response.status === 'on_track') {
        const nextStep = p.steps[stepIndex + 1]
        if (nextStep) {
          stepIdRef.current = nextStep.id
          setCurrentStepId(nextStep.id)
        } else {
          setIsComplete(true)
          stopCapture()
        }
      }
    } catch (err) {
      console.error('Guidance analysis error:', err)
    }
  }, [stopCapture])

  const startCapture = useCallback(async () => {
    const p = planRef.current
    if (!p || p.steps.length === 0) return

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      streamRef.current = stream
      setStream(stream)

      const video = document.createElement('video')
      video.srcObject = stream
      video.muted = true
      video.autoplay = true
      videoRef.current = video
      canvasRef.current = document.createElement('canvas')

      stepIdRef.current = p.steps[0].id
      setCurrentStepId(p.steps[0].id)
      setIsCapturing(true)
      setIsComplete(false)

      video.play().catch(() => {})

      video.onloadedmetadata = () => {
        timerRef.current = setInterval(captureAndAnalyze, intervalSecs * 1000)
      }

      // Handle user stopping screen share from the browser's native UI
      stream.getVideoTracks()[0].addEventListener('ended', stopCapture)
    } catch (err) {
      console.error('Screen capture error:', err)
    }
  }, [intervalSecs, captureAndAnalyze, stopCapture])

  return { isCapturing, isComplete, currentStepId, guidanceResponse, stream, startCapture, stopCapture }
}
