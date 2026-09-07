import { api } from './client'
import type { BulkPatchResult, Combination, CombinationStatus, Page } from '../types/api'

export interface CombinationFilter {
  status?: CombinationStatus
  factorValues?: [number, number][]
}

function filterToParams(filter: CombinationFilter, limit: number, offset: number): URLSearchParams {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (filter.status) params.set('status', filter.status)
  for (const [factorId, valueId] of filter.factorValues ?? []) {
    params.append('fv', `${factorId}:${valueId}`)
  }
  return params
}

export function listCombinations(
  tableId: number,
  filter: CombinationFilter = {},
  limit = 50,
  offset = 0,
) {
  const params = filterToParams(filter, limit, offset)
  return api.get<Page<Combination>>(`/decision-tables/${tableId}/combinations?${params}`)
}

export function patchCombination(
  tableId: number,
  combinationId: number,
  input: { status?: CombinationStatus; output?: string | null; impossible_reason?: string | null },
) {
  return api.patch<Combination>(`/decision-tables/${tableId}/combinations/${combinationId}`, input)
}

export function bulkPatchCombinations(
  tableId: number,
  filter: CombinationFilter,
  patch: { status?: CombinationStatus; output?: string | null; impossible_reason?: string | null },
) {
  return api.post<BulkPatchResult>(`/decision-tables/${tableId}/combinations/bulk-patch`, {
    filter: { status: filter.status, factor_values: filter.factorValues ?? [] },
    patch,
  })
}
