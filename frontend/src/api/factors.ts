import { api } from './client'
import type { Factor, FactorValue } from '../types/api'

export function addFactor(tableId: number, name: string) {
  return api.post<Factor>(`/decision-tables/${tableId}/factors`, { name })
}

export function updateFactor(
  tableId: number,
  factorId: number,
  input: { name?: string; order_index?: number },
) {
  return api.patch<Factor>(`/decision-tables/${tableId}/factors/${factorId}`, input)
}

export function deleteFactor(tableId: number, factorId: number) {
  return api.delete<void>(`/decision-tables/${tableId}/factors/${factorId}`)
}

export function addFactorValue(tableId: number, factorId: number, value: string) {
  return api.post<FactorValue>(`/decision-tables/${tableId}/factors/${factorId}/values`, { value })
}

export function updateFactorValue(
  tableId: number,
  factorId: number,
  valueId: number,
  input: { value?: string; order_index?: number },
) {
  return api.patch<FactorValue>(
    `/decision-tables/${tableId}/factors/${factorId}/values/${valueId}`,
    input,
  )
}

export function deleteFactorValue(tableId: number, factorId: number, valueId: number) {
  return api.delete<void>(`/decision-tables/${tableId}/factors/${factorId}/values/${valueId}`)
}
