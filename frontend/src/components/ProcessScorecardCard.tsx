import { ProcessScore } from '../api'

interface Props { data: ProcessScore | undefined }

export default function ProcessScorecardCard({ data }: Props) {
  if (!data) return null
  return (
    <div className="card">
      <h3>🎯 Process Scorecard</h3>
      <p className="muted small">Judge the process, not individual outcomes.</p>
      <div style={{ marginTop: 12, fontSize: '1.5em' }}>
        Composite (strict): <b>{data.composite}</b>
        <span className="muted small" style={{ marginLeft: 8 }}>← optimize this</span>
      </div>
      <table style={{ width: '100%', marginTop: 12 }}>
        <tbody>
          <tr><td>Rules followed</td><td align="right">{data.rules_followed_pct}%</td></tr>
          <tr><td>No mistakes</td><td align="right">{data.no_mistakes_pct}%</td></tr>
          <tr><td>Clean entries (all 4 conditions)</td><td align="right">{data.clean_pct}%</td></tr>
        </tbody>
      </table>
      <p className="muted small" style={{ marginTop: 8 }}>
        Process bonus:{' '}
        <b style={{ color: data.process_winrate_minus_outcome_winrate >= 0 ? 'var(--green)' : 'var(--red)' }}>
          {data.process_winrate_minus_outcome_winrate >= 0 ? '+' : ''}
          {data.process_winrate_minus_outcome_winrate} pp
        </b>{' '}
        WR when sample is clean.
      </p>
    </div>
  )
}
