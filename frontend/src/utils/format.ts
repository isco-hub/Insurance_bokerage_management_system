export const CURRENCY_LOCALE = 'en-UG';
export const CURRENCY_CODE = 'UGX';

const currencyFormatter = new Intl.NumberFormat(CURRENCY_LOCALE, {
  style: 'currency',
  currency: CURRENCY_CODE,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat(CURRENCY_LOCALE, {
  style: 'currency',
  currency: CURRENCY_CODE,
  notation: 'compact',
  maximumFractionDigits: 1,
});

const numberFormatter = new Intl.NumberFormat(CURRENCY_LOCALE, {
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
});

const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatCurrency(value: unknown, compact = false): string {
  if (value === null || value === undefined || value === '') return '—';
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return compact
    ? compactCurrencyFormatter.format(numeric)
    : currencyFormatter.format(numeric);
}

export function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numberFormatter.format(numeric);
}

function parseDate(value: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T00:00:00`);
  }
  return new Date(value);
}

export function formatDate(value: unknown): string {
  if (!value) return '—';
  const parsed = parseDate(String(value));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return dateFormatter.format(parsed);
}

export function formatDateTime(value: unknown): string {
  if (!value) return '—';
  const parsed = parseDate(String(value));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return dateTimeFormatter.format(parsed);
}

export function titleCase(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  return String(value)
    .replace(/[_-]+/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function formatValue(
  value: unknown,
  format?: 'currency' | 'date' | 'datetime' | 'boolean' | 'number',
): string {
  if (format === 'currency') return formatCurrency(value);
  if (format === 'date') return formatDate(value);
  if (format === 'datetime') return formatDateTime(value);
  if (format === 'boolean') return value ? 'Yes' : 'No';
  if (format === 'number') return formatNumber(value);
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function toDateTimeLocal(value: unknown): string {
  if (!value) return '';
  const parsed = new Date(String(value));
  if (Number.isNaN(parsed.getTime())) return String(value);
  const pad = (part: number) => String(part).padStart(2, '0');
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(
    parsed.getDate(),
  )}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

const TONES: Record<string, string> = {
  ACTIVE: 'success',
  APPROVED: 'success',
  PAID: 'success',
  CONFIRMED: 'success',
  WON: 'success',
  SETTLED: 'success',
  RECONCILED: 'success',
  DONE: 'success',
  VERIFIED: 'success',
  CURRENT: 'success',
  ISSUED: 'info',
  RECEIVED: 'info',
  SENT: 'info',
  IN_PROGRESS: 'info',
  UNDER_REVIEW: 'info',
  QUOTED: 'info',
  SELECTED: 'info',
  RESERVED: 'warning',
  PARTIAL: 'warning',
  PENDING: 'warning',
  PENDING_APPROVAL: 'warning',
  DUE: 'warning',
  UPCOMING: 'warning',
  DRAFT: 'neutral',
  TODO: 'neutral',
  NEW: 'info',
  OVERDUE: 'danger',
  EXPIRED: 'danger',
  REJECTED: 'danger',
  LOST: 'danger',
  LAPSED: 'danger',
  CANCELLED: 'danger',
  REVERSED: 'danger',
  DECLINED: 'danger',
  WAIVED: 'neutral',
  CLOSED: 'neutral',
  HIGH: 'danger',
  URGENT: 'danger',
  MEDIUM: 'warning',
  LOW: 'info',
};

export function statusTone(value: unknown): string {
  return TONES[String(value ?? '').toUpperCase()] ?? 'neutral';
}
