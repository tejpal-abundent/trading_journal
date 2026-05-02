import { StreakExpectations } from '../api'

interface Props { data: StreakExpectations | undefined }

export default function DontBailBanner({ data }: Props) {
  if (!data || 'insufficient_data' in data) return null
  if (data.current_streak.kind !== 'loss') return null
  if (data.current_streak.length < 2) return null

  const lossPct = Math.round(data.p_loss * 100)
  const expected = data.expected_max_loss_streak
  const actual = data.current_streak.length

  if (actual <= expected) {
    return (
      <div className="banner banner-info" style={{
        padding: 12, borderRadius: 6, marginBottom: 12,
        background: 'var(--blue-bg)', color: 'var(--blue)',
      }}>
        ℹ {actual} losses in a row is normal at your {lossPct}% loss rate.
        Expected max streak in this sample is {expected}. Don't tilt — keep the system.
      </div>
    )
  }

  return (
    <div className="banner banner-warn" style={{
      padding: 12, borderRadius: 6, marginBottom: 12,
      background: 'var(--yellow-bg)', color: 'var(--yellow)',
    }}>
      ⚠ {actual}-loss streak exceeds the {expected} expected for this sample.
      Could be variance, could be a regime shift. Review before next trade.
    </div>
  )
}
