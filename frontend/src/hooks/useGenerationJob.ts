import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/generation'
import type { GenerationJobStatus } from '../types/api'

const TERMINAL: GenerationJobStatus[] = ['completed', 'failed', 'cancelled']

/** Polls while the job is pending/running, stops automatically once it
 * reaches a terminal state. */
export function useGenerationJob(tableId: number, jobId: number | undefined) {
  return useQuery({
    queryKey: ['generationJob', tableId, jobId],
    queryFn: () => api.getGenerationJob(tableId, jobId as number),
    enabled: jobId !== undefined,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && TERMINAL.includes(status) ? false : 1000
    },
  })
}

export function useRequestGeneration(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.requestGeneration(tableId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisionTables', tableId] }),
  })
}

export function useCancelGenerationJob(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => api.cancelGenerationJob(tableId, jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['generationJob', tableId] }),
  })
}
