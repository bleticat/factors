import { api } from './client'
import type { GenerationJob } from '../types/api'

export function requestGeneration(tableId: number) {
  return api.post<GenerationJob>(`/decision-tables/${tableId}/generation-jobs`)
}

export function getGenerationJob(tableId: number, jobId: number) {
  return api.get<GenerationJob>(`/decision-tables/${tableId}/generation-jobs/${jobId}`)
}

export function cancelGenerationJob(tableId: number, jobId: number) {
  return api.post<GenerationJob>(`/decision-tables/${tableId}/generation-jobs/${jobId}/cancel`)
}
