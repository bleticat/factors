import { api } from './client'
import type { Page, ReapplyRulesResult, Rule, RuleRef } from '../types/api'

export function listRules(tableId: number, limit = 50, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return api.get<Page<Rule>>(`/decision-tables/${tableId}/rules?${params}`)
}

export function createRule(tableId: number, factorValues: [number, number][], output: string) {
  return api.post<RuleRef>(`/decision-tables/${tableId}/rules`, {
    factor_values: factorValues,
    output,
  })
}

export function deleteRule(tableId: number, ruleId: number) {
  return api.delete<void>(`/decision-tables/${tableId}/rules/${ruleId}`)
}

export function reapplyRules(tableId: number) {
  return api.post<ReapplyRulesResult>(`/decision-tables/${tableId}/rules/reapply`)
}
