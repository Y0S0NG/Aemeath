import type { GuidanceResponse } from './types'

declare global {
  interface Window {
    electronAPI: {
      getScreenSources: () => Promise<Array<{ id: string; name: string }>>
      showOverlay: () => void
      hideOverlay: () => void
      sendOverlayUpdate: (data: GuidanceResponse) => void
      onOverlayUpdate: (cb: (data: GuidanceResponse) => void) => () => void
      setIgnoreMouseEvents: (ignore: boolean) => void
    }
  }
}

export {}
