import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/decisionTables'

export function useDecisionTables(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['decisionTables', { limit, offset }],
    queryFn: () => api.listDecisionTables(limit, offset),
  })
}

export function useDecisionTable(tableId: number | undefined) {
  return useQuery({
    queryKey: ['decisionTables', tableId],
    queryFn: () => api.getDecisionTable(tableId as number),
    enabled: tableId !== undefined,
  })
}

export function useCreateDecisionTable() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createDecisionTable,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisionTables'] }),
  })
}

export function useDeleteDecisionTable() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (tableId: number) => api.deleteDecisionTable(tableId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisionTables'] }),
  })
}
