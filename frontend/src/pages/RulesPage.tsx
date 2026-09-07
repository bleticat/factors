import { useState } from 'react'
import { useParams } from 'react-router-dom'
import TableNav from '../components/TableNav'
import { useCombinations } from '../hooks/useCombinations'
import { useDecisionTable } from '../hooks/useDecisionTables'
import {
  useCreateRule,
  useDeleteRule,
  useReapplyRules,
  useReorderRules,
  useRuleOverlaps,
  useRules,
  useUpdateRule,
} from '../hooks/useRules'
import type { DecisionTable, Rule, RuleValue } from '../types/api'

const OVERLAPS_PAGE_SIZE = 20

type Assignment = Record<number, number | undefined>

function assignmentToFactorValues(assignment: Assignment): [number, number][] {
  return Object.entries(assignment)
    .filter((entry): entry is [string, number] => entry[1] !== undefined)
    .map(([factorId, valueId]) => [Number(factorId), valueId])
}

function assignmentFromRule(rule: Rule): Assignment {
  return Object.fromEntries(rule.factor_values.map((fv) => [fv.factor_id, fv.factor_value_id]))
}

// Shared per-factor "any / specific value" select grid, used by both the
// "New rule" form and the rule editor below.
function AssignmentFields({
  table,
  value,
  onChange,
}: {
  table: DecisionTable
  value: Assignment
  onChange: (factorId: number, valueId: number | undefined) => void
}) {
  return (
    <div className="row-wrap">
      {table.factors.map((factor) => (
        <label key={factor.id}>
          {factor.name}:{' '}
          <select
            value={value[factor.id] ?? ''}
            onChange={(e) => onChange(factor.id, e.target.value ? Number(e.target.value) : undefined)}
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
  )
}

export default function RulesPage() {
  const { tableId: tableIdParam } = useParams()
  const tableId = Number(tableIdParam)
  const { data: table } = useDecisionTable(tableId)
  const { data: rulesPage } = useRules(tableId)
  const createRule = useCreateRule(tableId)
  const updateRule = useUpdateRule(tableId)
  const deleteRule = useDeleteRule(tableId)
  const reapplyRules = useReapplyRules(tableId)
  const reorderRules = useReorderRules(tableId)

  const [overlapsOffset, setOverlapsOffset] = useState(0)
  const { data: overlapsPage } = useRuleOverlaps(tableId, OVERLAPS_PAGE_SIZE, overlapsOffset)

  const [assignment, setAssignment] = useState<Assignment>({})
  const [output, setOutput] = useState('')
  const [title, setTitle] = useState('')

  const factorValues = assignmentToFactorValues(assignment)

  // Live "how many rows would this affect" preview — same filter shape as
  // the combinations list/bulk-patch (spec 003), just before it's saved as
  // a rule. Only the count is needed, so limit=1 keeps the response small.
  const { data: preview } = useCombinations(tableId, { factorValues }, 1, 0)

  // The rule editor: content only (title/output/assignment) — order lives
  // exclusively in the "Saved rules" drag-and-drop below (spec 009). Any
  // assignment is accepted regardless of how it relates to other rules; a
  // rule that ends up hidden behind another is surfaced as "shadowed"
  // rather than blocked.
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editAssignment, setEditAssignment] = useState<Assignment>({})
  const [editOutput, setEditOutput] = useState('')
  const [editTitle, setEditTitle] = useState('')

  const [draggedId, setDraggedId] = useState<number | null>(null)

  if (!table) return <p className="muted">Loading…</p>

  function valueLabel(factorId: number, valueId: number): string {
    const factor = table!.factors.find((f) => f.id === factorId)
    return factor?.values.find((v) => v.id === valueId)?.value ?? String(valueId)
  }

  function describeAssignment(factorValues: RuleValue[]): string {
    if (factorValues.length === 0) return 'any combination'
    return factorValues
      .map((fv) => {
        const factor = table!.factors.find((f) => f.id === fv.factor_id)
        return `${factor?.name ?? fv.factor_id} = ${valueLabel(fv.factor_id, fv.factor_value_id)}`
      })
      .join(', ')
  }

  // The title is purely a human-readable label (spec 005); fall back to the
  // output wherever a short label for a rule is needed but no title was set.
  function ruleLabel(rule: { title: string | null; output: string }): string {
    return rule.title ?? rule.output
  }

  function formatTimestamp(value: string): string {
    // Naive UTC timestamps from the backend; append 'Z' so Date parses them
    // as UTC instead of local time.
    return new Date(`${value}Z`).toLocaleString()
  }

  function handleSave() {
    if (!output.trim()) return
    createRule.mutate(
      { factorValues, output, title: title.trim() || undefined },
      { onSuccess: () => { setAssignment({}); setOutput(''); setTitle('') } },
    )
  }

  function startEdit(rule: Rule) {
    setEditingId(rule.id)
    setEditAssignment(assignmentFromRule(rule))
    setEditOutput(rule.output)
    setEditTitle(rule.title ?? '')
  }

  function cancelEdit() {
    setEditingId(null)
  }

  function saveEdit() {
    if (editingId === null || !editOutput.trim()) return
    updateRule.mutate(
      {
        ruleId: editingId,
        output: editOutput,
        title: editTitle.trim() || null,
        factorValues: assignmentToFactorValues(editAssignment),
      },
      { onSuccess: () => setEditingId(null) },
    )
  }

  // Drag-and-drop reordering lives here, on "Saved rules" — the only place
  // apply order changes (spec 009). Any resulting order is accepted.
  function handleDrop(targetId: number) {
    if (!rulesPage || draggedId === null || draggedId === targetId) {
      setDraggedId(null)
      return
    }
    const orderedIds = rulesPage.items.map((r) => r.id)
    const from = orderedIds.indexOf(draggedId)
    const to = orderedIds.indexOf(targetId)
    orderedIds.splice(from, 1)
    orderedIds.splice(to, 0, draggedId)
    reorderRules.mutate(orderedIds)
    setDraggedId(null)
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
        <AssignmentFields
          table={table}
          value={assignment}
          onChange={(factorId, valueId) =>
            setAssignment((prev) => ({ ...prev, [factorId]: valueId }))
          }
        />
        <div className="row-wrap">
          <input
            type="text"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ flex: 1, minWidth: '12rem' }}
          />
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

      {editingId !== null && (
        <div className="card stack">
          <strong>Editing rule #{editingId}</strong>
          <p className="muted">
            Change the title, output, or however many factors this rule depends on. Its position in the
            apply order is unaffected — drag it in "Saved rules" below if you also need to move it.
          </p>
          <AssignmentFields
            table={table}
            value={editAssignment}
            onChange={(factorId, valueId) =>
              setEditAssignment((prev) => ({ ...prev, [factorId]: valueId }))
            }
          />
          <div className="row-wrap">
            <input
              type="text"
              placeholder="Title (optional)"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              style={{ flex: 1, minWidth: '12rem' }}
            />
            <input
              type="text"
              placeholder="Output"
              value={editOutput}
              onChange={(e) => setEditOutput(e.target.value)}
              style={{ flex: 1, minWidth: '16rem' }}
            />
          </div>
          <div className="row-wrap">
            <button className="primary" disabled={!editOutput.trim() || updateRule.isPending} onClick={saveEdit}>
              Save
            </button>
            <button onClick={cancelEdit} disabled={updateRule.isPending}>
              Cancel
            </button>
          </div>
          {updateRule.isError && <p className="error-text">{(updateRule.error as Error).message}</p>}
        </div>
      )}

      <div className="card">
        <strong>Saved rules</strong>
        <p className="muted">
          Drag a row by its handle to change apply order. Rules earlier in the list are replayed first;
          where two rules match the same row, the last (bottom-most) one wins. Any order is allowed — a
          rule hidden behind a later one is flagged below as <strong>shadowed</strong> rather than blocked,
          so it's on you to notice and, if needed, drag it lower or edit it.
        </p>
        {rulesPage && rulesPage.items.length === 0 && (
          <p className="muted">
            No rules yet — rules created here re-apply automatically whenever this table is regenerated.
          </p>
        )}
        {reorderRules.isError && (
          <p className="error-text">{(reorderRules.error as Error).message}</p>
        )}
        {rulesPage && rulesPage.items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Title</th>
                <th>When</th>
                <th>Output</th>
                <th>Rows affected</th>
                <th>Shadowed</th>
                <th>Last applied</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rulesPage.items.map((rule) => {
                const fullyShadowed = rule.matched_count > 0 && rule.shadowed_count >= rule.matched_count
                const partiallyShadowed = rule.shadowed_count > 0 && !fullyShadowed
                return (
                  <tr
                    key={rule.id}
                    draggable={editingId === null}
                    onDragStart={() => setDraggedId(rule.id)}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => handleDrop(rule.id)}
                    style={{
                      cursor: editingId === null ? 'grab' : undefined,
                      opacity: draggedId === rule.id ? 0.5 : 1,
                      background: editingId === rule.id ? 'var(--highlight, rgba(127,127,255,0.08))' : undefined,
                    }}
                  >
                    <td className="muted" title="Drag to reorder">
                      ⠿
                    </td>
                    <td>{rule.title ?? <span className="muted">—</span>}</td>
                    <td>{describeAssignment(rule.factor_values)}</td>
                    <td>{rule.output}</td>
                    <td>{rule.matched_count}</td>
                    <td>
                      {fullyShadowed && (
                        <span className="error-text" title="Every matched row is shadowed — this rule's output currently appears nowhere.">
                          ⚠ all {rule.shadowed_count}
                        </span>
                      )}
                      {partiallyShadowed && (
                        <span title="Some matched rows are shadowed by a later rule.">
                          ⚠ {rule.shadowed_count} of {rule.matched_count}
                        </span>
                      )}
                      {!fullyShadowed && !partiallyShadowed && <span className="muted">—</span>}
                    </td>
                    <td className="muted">
                      {rule.applied_at ? formatTimestamp(rule.applied_at) : 'not applied yet'}
                    </td>
                    <td className="row-wrap">
                      <button onClick={() => startEdit(rule)} disabled={editingId !== null}>
                        Edit
                      </button>
                      <button
                        className="danger"
                        onClick={() => deleteRule.mutate(rule.id)}
                        disabled={deleteRule.isPending || editingId !== null}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <strong>Rows affected by multiple rules</strong>
        <p className="muted">
          These rows match two or more of the rules above. The last (bold) rule listed for each row is the
          one whose output currently wins — the others are hidden on that row, shown dimmed below.
        </p>
        {overlapsPage && overlapsPage.total === 0 && (
          <p className="muted">No rows are currently matched by more than one rule.</p>
        )}
        {overlapsPage && overlapsPage.total > 0 && (
          <>
            <table>
              <thead>
                <tr>
                  {table.factors.map((f) => (
                    <th key={f.id}>{f.name}</th>
                  ))}
                  <th>Matching rules (winner last)</th>
                </tr>
              </thead>
              <tbody>
                {overlapsPage.items.map((item) => (
                  <tr key={item.combination.id}>
                    {table.factors.map((f) => {
                      const cv = item.combination.values.find((v) => v.factor_id === f.id)
                      return <td key={f.id}>{cv ? valueLabel(f.id, cv.factor_value_id) : '—'}</td>
                    })}
                    <td>
                      {item.matching_rules.map((r, i) => {
                        const isWinner = i === item.matching_rules.length - 1
                        return (
                          <span key={r.id}>
                            {i > 0 && ', '}
                            <span
                              className={isWinner ? undefined : 'muted'}
                              style={isWinner ? { fontWeight: 'bold' } : { textDecoration: 'line-through' }}
                              title={isWinner ? 'Currently wins on this row' : 'Hidden on this row'}
                            >
                              {ruleLabel(r)}
                            </span>
                          </span>
                        )
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {overlapsPage.total > OVERLAPS_PAGE_SIZE && (
              <div className="row" style={{ justifyContent: 'center', marginTop: '1rem' }}>
                <button
                  disabled={overlapsOffset === 0}
                  onClick={() => setOverlapsOffset(Math.max(0, overlapsOffset - OVERLAPS_PAGE_SIZE))}
                >
                  Previous
                </button>
                <span className="muted">
                  {overlapsOffset + 1}–{Math.min(overlapsOffset + OVERLAPS_PAGE_SIZE, overlapsPage.total)} of{' '}
                  {overlapsPage.total}
                </span>
                <button
                  disabled={overlapsOffset + OVERLAPS_PAGE_SIZE >= overlapsPage.total}
                  onClick={() => setOverlapsOffset(overlapsOffset + OVERLAPS_PAGE_SIZE)}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
