import { useState } from 'react'
import { useParams } from 'react-router-dom'
import BulkActionBar from '../components/BulkActionBar'
import CombinationsTable from '../components/CombinationsTable'
import TableNav from '../components/TableNav'
import { useBulkPatchCombinations, useCombinations, usePatchCombination } from '../hooks/useCombinations'
import { useDecisionTable } from '../hooks/useDecisionTables'
import { useRules } from '../hooks/useRules'
import type { CombinationStatus } from '../types/api'

const PAGE_SIZE = 50

export default function CombinationsPage() {
  const { tableId: tableIdParam } = useParams()
  const tableId = Number(tableIdParam)
  const { data: table } = useDecisionTable(tableId)
  const [statusFilter, setStatusFilter] = useState<CombinationStatus | undefined>(undefined)
  const [factorValueFilter, setFactorValueFilter] = useState<Record<number, number | undefined>>({})
  const [offset, setOffset] = useState(0)

  const factorValues: [number, number][] = Object.entries(factorValueFilter)
    .filter((entry): entry is [string, number] => entry[1] !== undefined)
    .map(([factorId, valueId]) => [Number(factorId), valueId])

  const filter = { status: statusFilter, factorValues }
  const { data: page, isLoading } = useCombinations(tableId, filter, PAGE_SIZE, offset)
  const { data: rulesPage } = useRules(tableId)
  const patchCombination = usePatchCombination(tableId)
  const bulkPatch = useBulkPatchCombinations(tableId)

  if (!table) return <p className="muted">Loading…</p>

  return (
    <div>
      <div className="page-header">
        <h1>{table.name} — Combinations</h1>
      </div>
      <TableNav tableId={tableId} />

      <div className="card row-wrap">
        <label>
          Status:{' '}
          <select
            value={statusFilter ?? ''}
            onChange={(e) => {
              setOffset(0)
              setStatusFilter(e.target.value ? (e.target.value as CombinationStatus) : undefined)
            }}
          >
            <option value="">any</option>
            <option value="unreviewed">unreviewed</option>
            <option value="possible">possible</option>
            <option value="impossible">impossible</option>
          </select>
        </label>
        {table.factors.map((factor) => (
          <label key={factor.id}>
            {factor.name}:{' '}
            <select
              value={factorValueFilter[factor.id] ?? ''}
              onChange={(e) => {
                setOffset(0)
                setFactorValueFilter((prev) => ({
                  ...prev,
                  [factor.id]: e.target.value ? Number(e.target.value) : undefined,
                }))
              }}
            >
              <option value="">any</option>
              {factor.values.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.value}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      <BulkActionBar
        matchCount={page?.total ?? 0}
        applying={bulkPatch.isPending}
        onApply={(patch) => bulkPatch.mutate({ filter, patch })}
      />

      {isLoading && <p className="muted">Loading…</p>}
      {page && page.items.length === 0 && <p className="muted">No combinations match this filter.</p>}
      {page && page.items.length > 0 && (
        <CombinationsTable
          table={table}
          combinations={page.items}
          rules={rulesPage?.items ?? []}
          onPatch={(id, input) => patchCombination.mutate({ combinationId: id, input })}
        />
      )}

      {page && page.total > PAGE_SIZE && (
        <div className="row" style={{ justifyContent: 'center', marginTop: '1rem' }}>
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </button>
          <span className="muted">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, page.total)} of {page.total}
          </span>
          <button disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Next
          </button>
        </div>
      )}
    </div>
  )
}
