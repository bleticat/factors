import { useState } from 'react'
import { useParams } from 'react-router-dom'
import TableNav from '../components/TableNav'
import { useCombinations } from '../hooks/useCombinations'
import { useDecisionTable } from '../hooks/useDecisionTables'
import { useCreateRule, useDeleteRule, useReapplyRules, useRules } from '../hooks/useRules'
import type { Rule } from '../types/api'

export default function RulesPage() {
  const { tableId: tableIdParam } = useParams()
  const tableId = Number(tableIdParam)
  const { data: table } = useDecisionTable(tableId)
  const { data: rulesPage } = useRules(tableId)
  const createRule = useCreateRule(tableId)
  const deleteRule = useDeleteRule(tableId)
  const reapplyRules = useReapplyRules(tableId)

  const [assignment, setAssignment] = useState<Record<number, number | undefined>>({})
  const [output, setOutput] = useState('')

  const factorValues: [number, number][] = Object.entries(assignment)
    .filter((entry): entry is [string, number] => entry[1] !== undefined)
    .map(([factorId, valueId]) => [Number(factorId), valueId])

  // Live "how many rows would this affect" preview — same filter shape as
  // the combinations list/bulk-patch (spec 003), just before it's saved as
  // a rule. Only the count is needed, so limit=1 keeps the response small.
  const { data: preview } = useCombinations(tableId, { factorValues }, 1, 0)

  if (!table) return <p className="muted">Loading…</p>

  function valueLabel(factorId: number, valueId: number): string {
    const factor = table!.factors.find((f) => f.id === factorId)
    return factor?.values.find((v) => v.id === valueId)?.value ?? String(valueId)
  }

  function describeRule(rule: Rule): string {
    if (rule.factor_values.length === 0) return 'any combination'
    return rule.factor_values
      .map((fv) => {
        const factor = table!.factors.find((f) => f.id === fv.factor_id)
        return `${factor?.name ?? fv.factor_id} = ${valueLabel(fv.factor_id, fv.factor_value_id)}`
      })
      .join(', ')
  }

  function formatTimestamp(value: string): string {
    // Naive UTC timestamps from the backend; append 'Z' so Date parses them
    // as UTC instead of local time.
    return new Date(`${value}Z`).toLocaleString()
  }

  function handleSave() {
    if (!output.trim()) return
    createRule.mutate(
      { factorValues, output },
      { onSuccess: () => { setAssignment({}); setOutput('') } },
    )
  }

  return (
    <div>
      <div className="page-header">
        <h1>{table.name} — Rules</h1>
        <button onClick={() => reapplyRules.mutate()} disabled={reapplyRules.isPending}>
          Reapply all rules
        </button>
      </div>
      <TableNav tableId={tableId} />

      <div className="card stack">
        <strong>New rule</strong>
        <p className="muted">
          Set values for the factors this rule depends on; leave the rest as "any" so it covers every
          value of that factor. Every row matching the assignment gets the output below, and stays
          covered when the table is regenerated later.
        </p>
        <div className="row-wrap">
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
        </div>
        <div className="row-wrap">
          <input
            type="text"
            placeholder="Output"
            value={output}
            onChange={(e) => setOutput(e.target.value)}
            style={{ flex: 1, minWidth: '16rem' }}
          />
          <button
            className="primary"
            disabled={!output.trim() || createRule.isPending}
            onClick={handleSave}
          >
            Save rule
          </button>
        </div>
        <span className="muted">{preview?.total ?? 0} row(s) currently match this assignment</span>
        {createRule.isSuccess && (
          <span className="muted">Saved — applied to {createRule.data.matched_count} row(s).</span>
        )}
        {createRule.isError && <p className="error-text">{(createRule.error as Error).message}</p>}
      </div>

      <div className="card">
        <strong>Saved rules</strong>
        {rulesPage && rulesPage.items.length === 0 && (
          <p className="muted">
            No rules yet — rules created here re-apply automatically whenever this table is regenerated.
          </p>
        )}
        {rulesPage && rulesPage.items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Output</th>
                <th>Rows affected</th>
                <th>Last applied</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rulesPage.items.map((rule) => (
                <tr key={rule.id}>
                  <td>{describeRule(rule)}</td>
                  <td>{rule.output}</td>
                  <td>{rule.matched_count}</td>
                  <td className="muted">
                    {rule.applied_at ? formatTimestamp(rule.applied_at) : 'not applied yet'}
                  </td>
                  <td>
                    <button
                      className="danger"
                      onClick={() => deleteRule.mutate(rule.id)}
                      disabled={deleteRule.isPending}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
