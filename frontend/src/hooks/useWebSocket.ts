import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/stores/authStore'

interface UseWebSocketOptions {
  url: string
  onMessage: (data: unknown) => void
  enabled?: boolean
}

export function useWebSocket({ url, onMessage, enabled = true }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const maxRetryDelay = 30_000

  const connect = useCallback(() => {
    if (!enabled) return

    const token = useAuthStore.getState().accessToken || ''
    // Prepend /api if the URL doesn't already include it (WebSocket routes live under /api/)
    const wsPath = url.startsWith('/api') ? url : `/api${url}`
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${wsPath}${wsPath.includes('?') ? '&' : '?'}token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      retryRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {}
    }

    ws.onclose = () => {
      if (!enabled) return
      // Exponential backoff reconnection (max 30s)
      const delay = Math.min(1000 * 2 ** retryRef.current, maxRetryDelay)
      retryRef.current++
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [url, onMessage, enabled])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }, [])

  return { send }
}
