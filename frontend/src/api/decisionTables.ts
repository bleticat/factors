import { api } from './client'
import type { DecisionTable, DecisionTableSummary, Page } from '../types/api'

export function listDecisionTables(limit = 50, offset = 0) {
  return api.get<Page<DecisionTableSummary>>(`/decision-tables?limit=${limit}&offset=${offset}`)
}

export function getDecisionTable(tableId: number) {
  return api.get<DecisionTable>(`/decision-tables/${tableId}`)
}

export function createDecisionTable(input: { name: string; description?: string | null }) {
  return api.post<DecisionTable>('/decision-tables', input)
}

export function updateDecisionTable(
  tableId: number,
  input: { name?: string; description?: string | null },
) {
  return api.patch<DecisionTable>(`/decision-tables/${tableId}`, input)
}

export function deleteDecisionTable(tableId: number) {
  return api.delete<void>(`/decision-tables/${tableId}`)
}
