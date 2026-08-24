import { useCallback, useEffect, useState } from 'react'
import type { ApiResult, DataSource } from '../types'

export function useApiResource<T>(loader: () => Promise<ApiResult<T>>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [source, setSource] = useState<DataSource>('demo')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // The caller controls loader identity through dependencies.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await loader()
      setData(result.data)
      setSource(result.source)
    } catch (value) {
      setError(value instanceof Error ? value : new Error('Unknown loading error'))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  useEffect(() => {
    void load()
  }, [load])

  return { data, source, loading, error, reload: load }
}
