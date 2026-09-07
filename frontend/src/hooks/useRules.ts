import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/rules'

export function useRules(tableId: number) {
  return useQuery({
    queryKey: ['rules', tableId],
    queryFn: () => api.listRules(tableId, 100, 0),
  })
}

export function useCreateRule(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ factorValues, output }: { factorValues: [number, number][]; output: string }) =>
      api.createRule(tableId, factorValues, output),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}

export function useDeleteRule(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ruleId: number) => api.deleteRule(tableId, ruleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules', tableId] }),
  })
}

export function useReapplyRules(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.reapplyRules(tableId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}
