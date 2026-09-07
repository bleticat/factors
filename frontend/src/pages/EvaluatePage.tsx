import { useMutation } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useParams } from 'react-router-dom'
import { evaluate } from '../api/evaluate'
import TableNav from '../components/TableNav'
import { useDecisionTable } from '../hooks/useDecisionTables'

export default function EvaluatePage() {
  const { tableId: tableIdParam } = useParams()
  const tableId = Number(tableIdParam)
  const { data: table } = useDecisionTable(tableId)
  const [assignment, setAssignment] = useState<Record<number, number | undefined>>({})
  const evaluateMutation = useMutation({
    mutationFn: (pairs: [number, number][]) => evaluate(tableId, pairs, 100, 0),
  })

  if (!table) return <p className="muted">Loading…</p>

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const pairs: [number, number][] = Object.entries(assignment)
      .filter((entry): entry is [string, number] => entry[1] !== undefined)
      .map(([factorId, valueId]) => [Number(factorId), valueId])
    evaluateMutation.mutate(pairs)
  }

  function valueLabel(factorId: number, valueId: number): string {
    const factor = table!.factors.find((f) => f.id === factorId)
    return factor?.values.find((v) => v.id === valueId)?.value ?? String(valueId)
  }

  const result = evaluateMutation.data

  return (
    <div>
      <div className="page-header">
        <h1>{table.name} — Evaluate</h1>
      </div>
      <TableNav tableId={tableId} />

      <form className="card row-wrap" onSubmit={handleSubmit}>
        {table.factors.map((factor) => (
          <label key={factor.id}>
            {factor.name}:{' '}
            <select
              value={assignment[factor.id] ?? ''}
              onChange={(e) =>
                setAssignment((prev) => ({
                  ...prev,
                  [factor.id]: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
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
        <button className="primary" type="submit" disabled={evaluateMutation.isPending}>
          Evaluate
        </button>
      </form>

      {evaluateMutation.isError && (
        <p className="error-text">{(evaluateMutation.error as Error).message}</p>
      )}

      {result?.kind === 'single' && (
        <div className="card">
          {result.combination ? (
            <>
              <span className={`badge ${result.combination.status}`}>{result.combination.status}</span>
              {result.combination.status === 'possible' && (
                <p>{result.combination.output || <span className="muted">No output set</span>}</p>
              )}
              {result.combination.status === 'impossible' && (
                <p>{result.combination.impossible_reason || <span className="muted">No reason set</span>}</p>
              )}
              {result.combination.status === 'unreviewed' && <p className="muted">Not reviewed yet.</p>}
            </>
          ) : (
            <p className="muted">
              No matching combination — has the table been generated since these factors/values were
              added?
            </p>
          )}
        </div>
      )}

      {result?.kind === 'list' && result.page && (
        <div className="card">
          <p className="muted">{result.page.total} matching combination(s)</p>
          <table>
            <thead>
              <tr>
                {table.factors.map((f) => (
                  <th key={f.id}>{f.name}</th>
                ))}
                <th>Status</th>
                <th>Output / reason</th>
              </tr>
            </thead>
            <tbody>
              {result.page.items.map((combo) => (
                <tr key={combo.id}>
                  {table.factors.map((f) => {
                    const cv = combo.values.find((v) => v.factor_id === f.id)
                    return <td key={f.id}>{cv ? valueLabel(f.id, cv.factor_value_id) : '—'}</td>
                  })}
                  <td>
                    <span className={`badge ${combo.status}`}>{combo.status}</span>
                  </td>
                  <td>
                    {combo.status === 'possible'
                      ? combo.output
                      : combo.status === 'impossible'
                        ? combo.impossible_reason
                        : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
