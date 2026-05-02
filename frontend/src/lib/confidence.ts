import { CIDecoration } from '../api'

/**
 * Format a percentage with its 95% Wilson CI half-width and confidence
 * label. Example output: "61.1% +/-9 (n=18, Noisy)".
 */
export function formatRateWithCI(rate: number, deco: CIDecoration | undefined): string {
  if (!deco) return `${rate}%`
  const n = deco.n ?? 0
  const ci = deco.win_rate_ci
  const label = deco.confidence ?? confidenceLabel(n)
  if (!ci) return `${rate}% (n=${n})`
  const halfWidth = Math.round((ci[1] - ci[0]) / 2)
  return `${rate}% +/-${halfWidth} (n=${n}, ${label})`
}

export function confidenceLabel(n: number): string {
  if (n < 30) return 'Noise'
  if (n < 100) return 'Noisy'
  if (n < 500) return 'Reasonable'
  if (n < 1000) return 'Strong'
  return 'Conviction'
}

export function confidenceBadgeClass(label: string | undefined): string {
  switch (label) {
    case 'Noise':      return 'bg-red-100 text-red-700'
    case 'Noisy':      return 'bg-orange-100 text-orange-700'
    case 'Reasonable': return 'bg-yellow-100 text-yellow-700'
    case 'Strong':     return 'bg-green-100 text-green-700'
    case 'Conviction': return 'bg-emerald-100 text-emerald-700'
    default:           return 'bg-gray-100 text-gray-700'
  }
}
