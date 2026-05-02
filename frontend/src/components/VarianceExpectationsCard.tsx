import { StreakExpectations } from '../api'

interface Props { data: StreakExpectations | undefined }

export default function VarianceExpectationsCard({ data }: Props) {
  if (!data) return null
  if ('insufficient_data' in data) {
    return (
      <div className="card">
        <h3>📉 Variance Expectations</h3>
        <p className="muted">No closed trades yet.</p>
      </div>
    )
  }

  const lossPct = Math.round(data.p_loss * 100)
  return (
    <div className="card">
      <h3>📉 Variance Expectations</h3>
      <table style={{ width: '100%' }}>
        <tbody>
          <tr><td>Loss probability</td><td align="right"><b>{lossPct}%</b></td></tr>
          <tr><td>Expected max loss streak</td><td align="right"><b>{data.expected_max_loss_streak}</b></td></tr>
          <tr><td>Your actual max</td><td align="right"><b>{data.actual_max_loss_streak}</b></td></tr>
          <tr>
            <td>Current streak</td>
            <td align="right">
              <b>{data.current_streak.length}</b>{' '}
              {data.current_streak.kind !== 'none' ? data.current_streak.kind + (data.current_streak.length === 1 ? '' : 'es') : ''}
            </td>
          </tr>
        </tbody>
      </table>
      {data.five_loss_streak_every_n_trades !== null && (
        <p className="muted small" style={{ marginTop: 8 }}>
          At your loss rate, a 5-loss streak starts roughly once every{' '}
          <b>{data.five_loss_streak_every_n_trades}</b> trades.
          Don't quit at normal variance.
        </p>
      )}
      <p className="muted small" style={{ marginTop: 4, fontStyle: 'italic' }}>
        {data.fat_tail_caveat}
      </p>
    </div>
  )
}
