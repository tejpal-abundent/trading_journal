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

/** Today's date as YYYY-MM-DD, local time (matches the `date` type the API expects). */
export const todayISO = (): string => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

/** Add/subtract whole days from an ISO date string, staying in YYYY-MM-DD form. */
export const shiftISODate = (iso: string, days: number): string => {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt.toISOString().slice(0, 10);
};

/** "2026-08-16" -> "Aug 16, 2026" */
export const formatDateLong = (iso: string): string => {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
};
