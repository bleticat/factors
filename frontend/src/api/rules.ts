import { api } from './client'
import type { CombinationOverlap, Page, ReapplyRulesResult, Rule } from '../types/api'

export function listRules(tableId: number, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return api.get<Page<Rule>>(`/decision-tables/${tableId}/rules?${params}`)
}

export function listRuleOverlaps(tableId: number, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return api.get<Page<CombinationOverlap>>(`/decision-tables/${tableId}/rules/overlaps?${params}`)
}

export function createRule(
  tableId: number,
  factorValues: [number, number][],
  output: string,
  title?: string,
) {
  return api.post<Rule>(`/decision-tables/${tableId}/rules`, {
    factor_values: factorValues,
    output,
    title: title || null,
  })
}

export function updateRule(
  tableId: number,
  ruleId: number,
  input: { output?: string; title?: string | null; factorValues?: [number, number][] },
) {
  return api.patch<Rule>(`/decision-tables/${tableId}/rules/${ruleId}`, {
    output: input.output,
    title: input.title,
    factor_values: input.factorValues,
  })
}

export function deleteRule(tableId: number, ruleId: number) {
  return api.delete<void>(`/decision-tables/${tableId}/rules/${ruleId}`)
}

export function reapplyRules(tableId: number) {
  return api.post<ReapplyRulesResult>(`/decision-tables/${tableId}/rules/reapply`)
}

export function reorderRules(tableId: number, orderedRuleIds: number[]) {
  return api.post<ReapplyRulesResult>(`/decision-tables/${tableId}/rules/reorder`, {
    ordered_rule_ids: orderedRuleIds,
  })
}
