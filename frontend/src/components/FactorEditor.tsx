import { type FormEvent, useState } from 'react'
import {
  useAddFactor,
  useAddFactorValue,
  useDeleteFactor,
  useDeleteFactorValue,
} from '../hooks/useFactors'
import type { DecisionTable } from '../types/api'

export default function FactorEditor({ table, locked }: { table: DecisionTable; locked: boolean }) {
  const tableId = table.id
  const addFactor = useAddFactor(tableId)
  const deleteFactor = useDeleteFactor(tableId)
  const addValue = useAddFactorValue(tableId)
  const deleteValue = useDeleteFactorValue(tableId)
  const [newFactorName, setNewFactorName] = useState('')
  const [newValueByFactor, setNewValueByFactor] = useState<Record<number, string>>({})

  function handleAddFactor(e: FormEvent) {
    e.preventDefault()
    if (!newFactorName.trim()) return
    addFactor.mutate(newFactorName, { onSuccess: () => setNewFactorName('') })
  }

  function handleAddValue(factorId: number) {
    const value = (newValueByFactor[factorId] ?? '').trim()
    if (!value) return
    addValue.mutate(
      { factorId, value },
      { onSuccess: () => setNewValueByFactor((prev) => ({ ...prev, [factorId]: '' })) },
    )
  }

  return (
    <div className="stack">
      {locked && (
        <p className="muted">
          A generation job is in progress — factors and values can&rsquo;t be edited until it
          finishes.
        </p>
      )}

      {table.factors.map((factor) => (
        <div key={factor.id} className="card">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <strong>{factor.name}</strong>
            <button
              className="danger"
              disabled={locked}
              onClick={() => deleteFactor.mutate(factor.id)}
            >
              Delete factor
            </button>
          </div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0' }}>
            {factor.values.map((value) => (
              <li
                key={value.id}
                className="row"
                style={{ justifyContent: 'space-between', padding: '0.15rem 0' }}
              >
                <span>{value.value}</span>
                <button
                  className="danger"
                  disabled={locked}
                  onClick={() => deleteValue.mutate({ factorId: factor.id, valueId: value.id })}
                >
                  Remove
                </button>
              </li>
            ))}
            {factor.values.length === 0 && <li className="muted">No values yet.</li>}
          </ul>
          <div className="row">
            <input
              type="text"
              placeholder="New value"
              disabled={locked}
              value={newValueByFactor[factor.id] ?? ''}
              onChange={(e) =>
                setNewValueByFactor((prev) => ({ ...prev, [factor.id]: e.target.value }))
              }
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddValue(factor.id)
                }
              }}
            />
            <button disabled={locked} onClick={() => handleAddValue(factor.id)}>
              Add value
            </button>
          </div>
        </div>
      ))}

      <form className="card row" onSubmit={handleAddFactor}>
        <input
          type="text"
          placeholder="New factor name"
          disabled={locked}
          value={newFactorName}
          onChange={(e) => setNewFactorName(e.target.value)}
        />
        <button className="primary" type="submit" disabled={locked || !newFactorName.trim()}>
          Add factor
        </button>
      </form>
    </div>
  )
}
