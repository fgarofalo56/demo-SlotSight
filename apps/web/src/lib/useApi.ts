import { useCallback, useEffect, useState } from 'react'
import { ApiError } from './api'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: ApiError | Error | null
  reload: () => void
}

/**
 * Load data from the API with loading and error states.
 *
 * Deliberately small — this app has no server-state library because it has no
 * mutations, no cache invalidation, and no optimistic updates. Reaching for
 * one here would be more machinery than the problem has.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | Error | null>(null)
  const [nonce, setNonce] = useState(0)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetcher()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)))
          setData(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { data, loading, error, reload }
}
