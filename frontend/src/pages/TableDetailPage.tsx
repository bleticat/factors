import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import FactorEditor from '../components/FactorEditor'
import GenerationProgress from '../components/GenerationProgress'
import TableNav from '../components/TableNav'
import { useDecisionTable } from '../hooks/useDecisionTables'
import { useCancelGenerationJob, useGenerationJob, useRequestGeneration } from '../hooks/useGenerationJob'

export default function TableDetailPage() {
  const { tableId: tableIdParam } = useParams()
  const tableId = Number(tableIdParam)
  const { data: table, isLoading, error } = useDecisionTable(tableId)
  const requestGeneration = useRequestGeneration(tableId)
  const cancelJob = useCancelGenerationJob(tableId)
  const [jobId, setJobId] = useState<number | undefined>(undefined)
  const { data: job } = useGenerationJob(tableId, jobId)

  const locked = job !== undefined && (job.status === 'pending' || job.status === 'running')

  if (isLoading) return <p className="muted">Loading…</p>
  if (error) return <p className="error-text">{(error as Error).message}</p>
  if (!table) return null

  const projectedTotal = table.factors.reduce((acc, f) => acc * f.values.length, table.factors.length > 0 ? 1 : 0)
  const canGenerate = table.factors.length > 0 && table.factors.every((f) => f.values.length > 0)

  function handleGenerate() {
    requestGeneration.mutate(undefined, { onSuccess: (newJob) => setJobId(newJob.id) })
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{table.name}</h1>
          {table.description && <p className="muted">{table.description}</p>}
        </div>
      </div>

      <TableNav tableId={tableId} />

      <div className="card stack">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <span>
            Projected combinations: <strong>{projectedTotal.toLocaleString()}</strong>
          </span>
          <div className="row">
            <button
              className="primary"
              disabled={!canGenerate || locked || requestGeneration.isPending}
              onClick={handleGenerate}
            >
              Generate combinations
            </button>
            {job && locked && <button onClick={() => cancelJob.mutate(job.id)}>Cancel</button>}
          </div>
        </div>
        {!canGenerate && (
          <p className="muted">
            Add at least one factor, and give every factor at least one value, to generate.
          </p>
        )}
        {requestGeneration.isError && (
          <p className="error-text">{(requestGeneration.error as Error).message}</p>
        )}
        {job && <GenerationProgress job={job} />}
        {job?.status === 'completed' && (
          <p>
            <Link to={`/tables/${tableId}/combinations`}>Review the generated combinations →</Link>
          </p>
        )}
      </div>

      <FactorEditor table={table} locked={locked} />
    </div>
  )
}
