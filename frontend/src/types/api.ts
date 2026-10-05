// Mirrors the shapes the backend's use cases return (backend/factors/features/*/entities.py,
// backend/factors/features/*/use_cases.py) — most of these are the actual domain
// entity/aggregate, not a separate read-only shadow of it.

export interface FactorValue {
  id: number
  value: string
  order_index: number
}

export interface Factor {
  id: number
  name: string
  order_index: number
  values: FactorValue[]
}

export interface DecisionTable {
  id: number
  name: string
  description: string | null
  factors: Factor[]
}

export interface DecisionTableSummary {
  id: number
  name: string
  description: string | null
  factor_count: number
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export type GenerationJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface GenerationJob {
  id: number
  decision_table_id: number
  status: GenerationJobStatus
  total_combinations: number
  created_count: number
  cursor: number
  error_message: string | null
  started_at: string | null
  finished_at: string | null
}

export type CombinationStatus = 'unreviewed' | 'possible' | 'impossible'

export interface CombinationValue {
  factor_id: number
  factor_value_id: number
}

export interface Combination {
  id: number
  decision_table_id: number
  generation_job_id: number
  signature: string
  status: CombinationStatus
  output: string | null
  impossible_reason: string | null
  values: CombinationValue[]
}

export interface EvaluateResult {
  kind: 'single' | 'list'
  combination: Combination | null
  page: Page<Combination> | null
}

export interface BulkPatchResult {
  matched_count: number
  updated_count: number
}

export interface RuleValue {
  factor_id: number
  factor_value_id: number
}

export interface Rule {
  id: number
  decision_table_id: number
  output: string
  title: string | null
  order_index: number
  factor_values: RuleValue[]
  matched_count: number
  applied_at: string | null
  created_at: string
  // How many of this rule's own matched rows are shadowed by a rule later
  // in apply order — i.e. currently show a different rule's output instead.
  shadowed_count: number
}

export interface ReapplyRulesResult {
  rules: Rule[]
}

export interface RuleTag {
  id: number
  output: string
  title: string | null
}

export interface CombinationOverlap {
  combination: Combination
  // Ordered by rule id ascending; the last entry is the rule that currently
  // wins a reapply (spec 005's "later-created rule wins").
  matching_rules: RuleTag[]
}
