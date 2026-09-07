import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from '../api/rules'

export function useRules(tableId: number) {
  return useQuery({
    queryKey: ['rules', tableId],
    queryFn: () => api.listRules(tableId, 100, 0),
  })
}

export function useRuleOverlaps(tableId: number, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['rule-overlaps', tableId, limit, offset],
    queryFn: () => api.listRuleOverlaps(tableId, limit, offset),
  })
}

export function useCreateRule(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      factorValues,
      output,
      title,
    }: {
      factorValues: [number, number][]
      output: string
      title?: string
    }) => api.createRule(tableId, factorValues, output, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['rule-overlaps', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}

export function useUpdateRule(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      ruleId,
      output,
      title,
      factorValues,
    }: {
      ruleId: number
      output?: string
      title?: string | null
      factorValues?: [number, number][]
    }) => api.updateRule(tableId, ruleId, { output, title, factorValues }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['rule-overlaps', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}

export function useReorderRules(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (orderedRuleIds: number[]) => api.reorderRules(tableId, orderedRuleIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['rule-overlaps', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}

export function useDeleteRule(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ruleId: number) => api.deleteRule(tableId, ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['rule-overlaps', tableId] })
    },
  })
}

export function useReapplyRules(tableId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.reapplyRules(tableId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules', tableId] })
      queryClient.invalidateQueries({ queryKey: ['rule-overlaps', tableId] })
      queryClient.invalidateQueries({ queryKey: ['combinations', tableId] })
    },
  })
}
