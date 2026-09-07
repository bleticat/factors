import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCreateDecisionTable, useDecisionTables, useDeleteDecisionTable } from '../hooks/useDecisionTables'

export default function TableListPage() {
  const { data, isLoading, error } = useDecisionTables(100, 0)
  const createTable = useCreateDecisionTable()
  const deleteTable = useDeleteDecisionTable()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    createTable.mutate(
      { name, description: description || null },
      {
        onSuccess: () => {
          setName('')
          setDescription('')
        },
      },
    )
  }

  return (
    <div>
      <div className="page-header">
        <h1>Decision Tables</h1>
      </div>

      <form className="card row-wrap" onSubmit={handleCreate}>
        <input type="text" placeholder="Table name" value={name} onChange={(e) => setName(e.target.value)} />
        <input
          type="text"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button className="primary" type="submit" disabled={createTable.isPending || !name.trim()}>
          Create table
        </button>
        {createTable.isError && <span className="error-text">{(createTable.error as Error).message}</span>}
      </form>

      {isLoading && <p className="muted">Loading…</p>}
      {error && <p className="error-text">{(error as Error).message}</p>}

      <ul className="table-list">
        {data?.items.map((table) => (
          <li key={table.id} className="card row">
            <div style={{ flex: 1 }}>
              <Link to={`/tables/${table.id}`}>
                <strong>{table.name}</strong>
              </Link>
              {table.description && <div className="muted">{table.description}</div>}
              <div className="muted">
                {table.factor_count} factor{table.factor_count === 1 ? '' : 's'}
              </div>
            </div>
            <button
              className="danger"
              onClick={() => {
                if (confirm(`Delete "${table.name}"? This cannot be undone.`)) deleteTable.mutate(table.id)
              }}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>

      {data && data.items.length === 0 && (
        <p className="muted">No decision tables yet — create one above.</p>
      )}
    </div>
  )
}
