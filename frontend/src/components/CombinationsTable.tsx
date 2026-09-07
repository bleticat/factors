import { useState } from 'react'
import type { Combination, CombinationStatus, DecisionTable } from '../types/api'

type PatchInput = { status?: CombinationStatus; output?: string | null; impossible_reason?: string | null }

interface Props {
  table: DecisionTable
  combinations: Combination[]
  onPatch: (combinationId: number, input: PatchInput) => void
}

function buildValueLookup(table: DecisionTable): Map<string, string> {
  const map = new Map<string, string>()
  for (const factor of table.factors) {
    for (const value of factor.values) {
      map.set(`${factor.id}:${value.id}`, value.value)
    }
  }
  return map
}

export default function CombinationsTable({ table, combinations, onPatch }: Props) {
  const lookup = buildValueLookup(table)

  return (
    <div style={{ overflowX: 'auto' }}>
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
          {combinations.map((combo) => (
            <CombinationRow key={combo.id} table={table} combo={combo} lookup={lookup} onPatch={onPatch} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CombinationRow({
  table,
  combo,
  lookup,
  onPatch,
}: {
  table: DecisionTable
  combo: Combination
  lookup: Map<string, string>
  onPatch: Props['onPatch']
}) {
  const [text, setText] = useState(
    combo.status === 'impossible' ? (combo.impossible_reason ?? '') : (combo.output ?? ''),
  )

  function handleStatusChange(status: CombinationStatus) {
    if (status === 'possible') onPatch(combo.id, { status, output: text || null, impossible_reason: null })
    else if (status === 'impossible')
      onPatch(combo.id, { status, impossible_reason: text || null, output: null })
    else onPatch(combo.id, { status })
  }

  function handleTextBlur() {
    if (combo.status === 'possible') onPatch(combo.id, { output: text || null })
    else if (combo.status === 'impossible') onPatch(combo.id, { impossible_reason: text || null })
  }

  return (
    <tr>
      {table.factors.map((f) => {
        const cv = combo.values.find((v) => v.factor_id === f.id)
        return <td key={f.id}>{cv ? lookup.get(`${f.id}:${cv.factor_value_id}`) : '—'}</td>
      })}
      <td>
        <select value={combo.status} onChange={(e) => handleStatusChange(e.target.value as CombinationStatus)}>
          <option value="unreviewed">unreviewed</option>
          <option value="possible">possible</option>
          <option value="impossible">impossible</option>
        </select>
      </td>
      <td>
        {combo.status !== 'unreviewed' && (
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onBlur={handleTextBlur}
            placeholder={combo.status === 'possible' ? 'expected output' : 'reason'}
          />
        )}
      </td>
    </tr>
  )
}
