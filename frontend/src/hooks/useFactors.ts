import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/factors'

function useInvalidateTable(tableId: number) {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ['decisionTables', tableId] })
    queryClient.invalidateQueries({ queryKey: ['decisionTables'] })
  }
}

export function useAddFactor(tableId: number) {
  const invalidate = useInvalidateTable(tableId)
  return useMutation({
    mutationFn: (name: string) => api.addFactor(tableId, name),
    onSuccess: invalidate,
  })
}

export function useUpdateFactor(tableId: number) {
  const invalidate = useInvalidateTable(tableId)
  return useMutation({
    mutationFn: ({
      factorId,
      input,
    }: {
      factorId: number
      input: { name?: string; order_index?: number }
    }) => api.updateFactor(tableId, factorId, input),
    onSuccess: invalidate,
  })
}

export function useDeleteFactor(tableId: number) {
  const invalidate = useInvalidateTable(tableId)
  return useMutation({
    mutationFn: (factorId: number) => api.deleteFactor(tableId, factorId),
    onSuccess: invalidate,
  })
}

export function useAddFactorValue(tableId: number) {
  const invalidate = useInvalidateTable(tableId)
  return useMutation({
    mutationFn: ({ factorId, value }: { factorId: number; value: string }) =>
      api.addFactorValue(tableId, factorId, value),
    onSuccess: invalidate,
  })
}

export function useDeleteFactorValue(tableId: number) {
  const invalidate = useInvalidateTable(tableId)
  return useMutation({
    mutationFn: ({ factorId, valueId }: { factorId: number; valueId: number }) =>
      api.deleteFactorValue(tableId, factorId, valueId),
    onSuccess: invalidate,
  })
}
