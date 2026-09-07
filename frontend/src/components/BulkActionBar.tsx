import { useState } from 'react'
import type { CombinationStatus } from '../types/api'

interface Patch {
  status: CombinationStatus
  output?: string
  impossible_reason?: string
}

interface Props {
  matchCount: number
  applying: boolean
  onApply: (patch: Patch) => void
}

export default function BulkActionBar({ matchCount, applying, onApply }: Props) {
  const [status, setStatus] = useState<CombinationStatus>('possible')
  const [text, setText] = useState('')

  function handleApply() {
    if (matchCount === 0) return
    if (!confirm(`Apply to ${matchCount} matching row(s)? This cannot be undone.`)) return
    if (status === 'possible') onApply({ status, output: text || undefined })
    else if (status === 'impossible') onApply({ status, impossible_reason: text || undefined })
    else onApply({ status })
  }

  return (
    <div className="card row-wrap">
      <strong>
        {matchCount} row{matchCount === 1 ? '' : 's'} match the current filter
      </strong>
      <select value={status} onChange={(e) => setStatus(e.target.value as CombinationStatus)}>
        <option value="possible">Mark possible</option>
        <option value="impossible">Mark impossible</option>
        <option value="unreviewed">Reset to unreviewed</option>
      </select>
      {status !== 'unreviewed' && (
        <input
          type="text"
          placeholder={status === 'possible' ? 'Output (optional)' : 'Reason (optional)'}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      )}
      <button className="primary" disabled={matchCount === 0 || applying} onClick={handleApply}>
        Apply to filtered rows
      </button>
    </div>
  )
}
