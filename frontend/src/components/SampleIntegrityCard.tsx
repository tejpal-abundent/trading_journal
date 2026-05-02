import { SampleIntegrity } from '../api'
import { confidenceBadgeClass } from '../lib/confidence'

interface Props { data: SampleIntegrity | undefined }

export default function SampleIntegrityCard({ data }: Props) {
  if (!data) return null

  if (data.clean_count === 0) {
    return (
      <div className="card">
        <h3>⚖️ Sample Integrity</h3>
        <p className="muted">
          No clean trades yet — log a trade with rules_followed=yes,
          no mistake tags, on-time entry, planned in advance.
        </p>
      </div>
    )
  }

  const ciHalfWidth = (ci: [number, number] | null) =>
    ci ? Math.round((ci[1] - ci[0]) / 2) : 0

  return (
    <div className="card">
      <h3>⚖️ Sample Integrity</h3>
      <div className="muted small">{data.definition}</div>
      <div style={{ marginTop: 8 }}>
        Clean trades: <b>{data.clean_count}</b> of {data.total_count}{' '}
        ({data.clean_pct}%)
      </div>
      <table style={{ marginTop: 8, width: '100%' }}>
        <tbody>
          <tr>
            <td>Clean win rate</td>
            <td align="right">
              <b>{data.clean_win_rate}%</b>
              {data.clean_win_rate_ci && (
                <> +/-{ciHalfWidth(data.clean_win_rate_ci)}</>
              )}{' '}
              <span className={`badge ${confidenceBadgeClass(data.clean_confidence)}`}>
                n={data.clean_count}, {data.clean_confidence}
              </span>
            </td>
          </tr>
          <tr>
            <td>All trades WR</td>
            <td align="right">
              {data.all_win_rate}%
              {data.all_win_rate_ci && (
                <> +/-{ciHalfWidth(data.all_win_rate_ci)}</>
              )}{' '}
              <span className={`badge ${confidenceBadgeClass(data.all_confidence)}`}>
                n={data.total_count}, {data.all_confidence}
              </span>
            </td>
          </tr>
          <tr>
            <td>Discipline edge</td>
            <td align="right">
              <b style={{ color: data.integrity_delta >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {data.integrity_delta >= 0 ? '+' : ''}{data.integrity_delta} pp
              </b>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
