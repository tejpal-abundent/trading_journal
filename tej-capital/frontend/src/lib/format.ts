export const pct = (v: number | null | undefined, digits = 2) =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;

export const num = (v: number | null | undefined, digits = 2) =>
  v == null ? "—" : v.toFixed(digits);

export const money = (v: number | null | undefined, currency = "USD") =>
  v == null ? "—" : new Intl.NumberFormat("en-US", {
    style: "currency", currency, maximumFractionDigits: 2,
  }).format(v);

export const withN = (formatted: string, n: number) =>
  `${formatted} · N=${n}`;
