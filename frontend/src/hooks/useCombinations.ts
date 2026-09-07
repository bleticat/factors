import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/combinations'
import type { CombinationFilter } from '../api/combinations'
import type { CombinationStatus } from '../types/api'

type PatchInput = { status?: CombinationStatus; output?: string | null; impossible_reason?: string | null }

export function useCombinations(
  tableId: number,
  filter: CombinationFilter,
  limit: number,
  offset: number,
) {
  return useQuery({
    queryKey: ['combinations', tableId, filter, limit, offset],
    queryFn: () => api.listCombinations(tableId, filter, limit, offset),
  })
}

export function usePatchCombination(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ combinationId, input }: { combinationId: number; input: PatchInput }) =>
      api.patchCombination(tableId, combinationId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['combinations', tableId] }),
  })
}

export function useBulkPatchCombinations(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ filter, patch }: { filter: CombinationFilter; patch: PatchInput }) =>
      api.bulkPatchCombinations(tableId, filter, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['combinations', tableId] }),
  })
}
