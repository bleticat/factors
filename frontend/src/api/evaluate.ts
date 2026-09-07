import { api } from './client'
import type { EvaluateResult } from '../types/api'

export function evaluate(tableId: number, assignment: [number, number][], limit = 50, offset = 0) {
  return api.post<EvaluateResult>(`/decision-tables/${tableId}/evaluate`, {
    assignment,
    limit,
    offset,
  })
}
