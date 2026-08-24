import { useCallback, useEffect, useRef, useState } from 'react'
import { api, runEventsUrl } from '../lib/api'
import type { DataSource, EvaluationRun } from '../types'

type Transport = 'connecting' | 'sse' | 'polling' | 'settled'

export function useLiveRun(runId: string | undefined) {
  const [run, setRun] = useState<EvaluationRun | null>(null)
  const [source, setSource] = useState<DataSource>('demo')
  const [transport, setTransport] = useState<Transport>('connecting')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const stopped = useRef(false)

  const refresh = useCallback(async () => {
    if (!runId || stopped.current) return null
    try {
      const result = await api.getRun(runId)
      setRun(result.data)
      setSource(result.source)
      setError(null)
      if (['completed', 'partial', 'failed', 'cancelled'].includes(result.data.status)) {
        setTransport('settled')
      }
      return result.data
    } catch (value) {
      setError(value instanceof Error ? value : new Error('Unable to load run'))
      return null
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => {
    const currentRunId = runId
    if (!currentRunId) {
      setLoading(false)
      setError(new Error('Run identifier is missing'))
      return
    }
    stopped.current = false
    setLoading(true)
    setTransport('connecting')
    let eventSource: EventSource | undefined
    let pollTimer: number | undefined
    let refreshTimer: number | undefined
    const isTerminal = (status: EvaluationRun['status']) =>
      ['completed', 'partial', 'failed', 'cancelled'].includes(status)

    const startPolling = () => {
      if (pollTimer || stopped.current) return
      setTransport('polling')
      pollTimer = window.setInterval(() => {
        void refresh().then((next) => {
          if (next && isTerminal(next.status)) {
            window.clearInterval(pollTimer)
            pollTimer = undefined
          }
        })
      }, 1_500)
    }

    const start = async () => {
      const initial = await refresh()
      if (!initial || stopped.current || isTerminal(initial.status)) {
        return
      }
      if (currentRunId.startsWith('demo-') || typeof EventSource === 'undefined') {
        startPolling()
        return
      }
      try {
        eventSource = new EventSource(runEventsUrl(currentRunId))
        eventSource.onopen = () => setTransport('sse')
        const scheduleRefresh = () => {
          window.clearTimeout(refreshTimer)
          refreshTimer = window.setTimeout(() => void refresh(), 80)
        }
        eventSource.onmessage = scheduleRefresh
        eventSource.addEventListener('progress', scheduleRefresh)
        eventSource.addEventListener('complete', () => {
          scheduleRefresh()
          eventSource?.close()
        })
        eventSource.onerror = () => {
          eventSource?.close()
          startPolling()
        }
      } catch {
        startPolling()
      }
    }
    void start()

    return () => {
      stopped.current = true
      eventSource?.close()
      window.clearInterval(pollTimer)
      window.clearTimeout(refreshTimer)
    }
  }, [refresh, runId])

  return { run, source, transport, loading, error, refresh }
}
