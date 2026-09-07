import type { GenerationJob } from '../types/api'

export default function GenerationProgress({ job }: { job: GenerationJob }) {
  const percent =
    job.total_combinations > 0 ? Math.round((job.created_count / job.total_combinations) * 100) : 0

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span>
          Status: <strong>{job.status}</strong>
        </span>
        <span className="muted">
          {job.created_count} / {job.total_combinations} combinations
        </span>
      </div>
      <div className="progress-bar">
        <div style={{ width: `${percent}%` }} />
      </div>
      {job.status === 'failed' && job.error_message && (
        <p className="error-text">{job.error_message}</p>
      )}
    </div>
  )
}
