import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Download,
  FileBarChart,
  RefreshCw,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { api, getErrorMessage } from '../api/client';
import { formatCurrency, formatDate, formatDateTime, formatNumber, titleCase } from '../utils/format';

interface ReportDefinition {
  key: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

const REPORTS: ReportDefinition[] = [
  {
    key: 'premium-production',
    label: 'Premium production',
    description: 'Premium written in the selected period.',
    icon: FileBarChart,
  },
  {
    key: 'business-mix',
    label: 'Business mix',
    description: 'Production split by insurer, class, branch and broker.',
    icon: BarChart3,
  },
  {
    key: 'commission',
    label: 'Commission register',
    description: 'Commission earned and its settlement status.',
    icon: BarChart3,
  },
  {
    key: 'commission-ageing',
    label: 'Commission ageing',
    description: 'Outstanding commission by age bucket.',
    icon: CalendarDays,
  },
  {
    key: 'commission-statement',
    label: 'Commission statement',
    description: 'Commission earned, outstanding and paid by insurer, class and product.',
    icon: BarChart3,
  },
  {
    key: 'remittance-reconciliation',
    label: 'Remittance reconciliation',
    description: 'Insurer remittances, bank matching and outstanding differences.',
    icon: FileBarChart,
  },
  {
    key: 'debtors-ageing',
    label: 'Debtors ageing',
    description: 'Outstanding client invoices by overdue age bucket.',
    icon: CalendarDays,
  },
  {
    key: 'quotation-conversion',
    label: 'Quotation conversion',
    description: 'Quotation pipeline, wins, losses and conversion by broker and class.',
    icon: RefreshCw,
  },
  {
    key: 'claim-analysis',
    label: 'Claims analysis',
    description: 'Claims reserve, settlement and recovery by insurer and class.',
    icon: BarChart3,
  },
  {
    key: 'business-by-client',
    label: 'Business by client',
    description: 'Premium and commission production ranked by client.',
    icon: BarChart3,
  },
  {
    key: 'policy-register',
    label: 'Policy register',
    description: 'Policy portfolio with premium, commission and current status.',
    icon: FileBarChart,
  },
  {
    key: 'premium-collections',
    label: 'Premium collections',
    description: 'Receipts collected by method and period.',
    icon: FileBarChart,
  },
  {
    key: 'outstanding-premiums',
    label: 'Outstanding premiums',
    description: 'Uncollected premium instalments and balances.',
    icon: FileBarChart,
  },
  {
    key: 'outstanding-debtors',
    label: 'Outstanding debtors',
    description: 'Unpaid invoices and client balances.',
    icon: FileBarChart,
  },
  {
    key: 'claims',
    label: 'Claims register',
    description: 'Claims notified, reserved, paid and recovered.',
    icon: BarChart3,
  },
  {
    key: 'renewals',
    label: 'Renewals',
    description: 'Renewal pipeline and outcomes.',
    icon: RefreshCw,
  },
  {
    key: 'staff-performance',
    label: 'Staff performance',
    description: 'Production and activity by team member.',
    icon: BarChart3,
  },
  {
    key: 'expiring-policies',
    label: 'Expiring policies',
    description: 'Active policies approaching expiry.',
    icon: CalendarDays,
  },
  {
    key: 'lost-business',
    label: 'Lost business',
    description: 'Renewals lost and the reasons why.',
    icon: FileBarChart,
  },
  {
    key: 'accounting',
    label: 'Accounting export',
    description: 'Invoices, receipts and credit/debit notes for accounting.',
    icon: FileBarChart,
  },
  {
    key: 'audit-summary',
    label: 'Audit summary',
    description: 'System activity by action and module.',
    icon: FileBarChart,
  },
];

const CURRENCY_KEYS = new Set([
  'premium',
  'total_premium',
  'premium_placed',
  'taxes',
  'amount',
  'total',
  'balance',
  'paid',
  'reserve',
  'recovered',
  'commission',
  'net_amount',
  'gross_premium',
  'commission_retained',
  'commission_amount',
  'matched_amount',
  'outstanding',
  'difference',
  'issued',
]);

const DATE_KEYS = new Set([
  'date',
  'date_of_loss',
  'due_date',
  'start_date',
  'end_date',
  'issue_date',
  'paid_at',
  'earned_at',
  'created_at',
  'requested_at',
  'decided_at',
  'lost_at',
  'period_from',
  'period_to',
  'from',
  'to',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function humanize(key: string): string {
  return titleCase(key);
}

function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  const stringValue = String(value);
  if (
    DATE_KEYS.has(key) ||
    /^\d{4}-\d{2}-\d{2}(T|$)/.test(stringValue)
  ) {
    return stringValue.includes('T') ? formatDateTime(stringValue) : formatDate(stringValue);
  }
  if (CURRENCY_KEYS.has(key) && typeof value !== 'boolean') {
    return formatCurrency(value);
  }
  if (typeof value === 'number') return formatNumber(value);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}

function columnsFor(rows: unknown[]): string[] {
  const columns: string[] = [];
  for (const row of rows.slice(0, 25)) {
    if (!isRecord(row)) continue;
    for (const key of Object.keys(row)) {
      if (!columns.includes(key)) columns.push(key);
    }
  }
  return columns;
}

function MiniTable({ title, rows }: { title: string; rows: unknown[] }) {
  const columns = columnsFor(rows);
  const validRows = rows.filter(isRecord);
  return (
    <section className="content-card mini-section">
      <div className="mini-section-head">
        <h3>{humanize(title)}</h3>
        <span className="badge badge-neutral">{validRows.length} rows</span>
      </div>
      <div className="table-wrap">
        <table className="data-table compact-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{humanize(column)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {validRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="table-empty">
                  No data available.
                </td>
              </tr>
            ) : (
              validRows.slice(0, 100).map((row, index) => (
                <tr key={String(row.id ?? index)}>
                  {columns.map((column) => (
                    <td key={column}>{formatCell(column, row[column])}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get('report') ?? REPORTS[0].key;
  const [selected, setSelected] = useState(
    REPORTS.some((report) => report.key === initial) ? initial : REPORTS[0].key,
  );
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const param = searchParams.get('report');
    if (param && REPORTS.some((report) => report.key === param)) {
      setSelected(param);
    }
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const params: Record<string, string> = {};
        if (from) params.from = from;
        if (to) params.to = to;
        const response = await api.get(`/reports/${selected}/`, { params });
        if (!cancelled) setData(response.data.data as Record<string, unknown>);
      } catch (caught) {
        if (!cancelled) {
          setError(getErrorMessage(caught));
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selected, from, to]);

  const definition = REPORTS.find((report) => report.key === selected) ?? REPORTS[0];

  const { rows, statEntries, reportSections } = useMemo(() => {
    if (!data) {
      return {
        rows: [] as unknown[],
        statEntries: [] as [string, unknown][],
        reportSections: [] as [string, unknown[]][],
      };
    }
    const summary = isRecord(data.summary) ? data.summary : {};
    const stats: [string, unknown][] = [];
    const sections: [string, unknown[]][] = [];

    for (const [key, value] of Object.entries(summary)) {
      if (Array.isArray(value)) {
        sections.push([key, value]);
      } else if (typeof value === 'number' || typeof value === 'string') {
        stats.push([key, value]);
      }
    }
    for (const [key, value] of Object.entries(data)) {
      if (['rows', 'summary'].includes(key)) continue;
      if (Array.isArray(value)) {
        sections.push([key, value]);
      } else if (typeof value === 'number' || typeof value === 'string') {
        stats.push([key, value]);
      }
    }
    return {
      rows: Array.isArray(data.rows) ? data.rows : [],
      statEntries: stats,
      reportSections: sections,
    };
  }, [data]);

  const rowColumns = columnsFor(rows);
  const validRows = rows.filter(isRecord);

  const chooseReport = (key: string) => {
    setSelected(key);
    const next = new URLSearchParams(searchParams);
    next.set('report', key);
    setSearchParams(next, { replace: true });
  };

  const exportCsv = async () => {
    setExporting(true);
    setError('');
    try {
      const params: Record<string, string> = {};
      if (from) params.from = from;
      if (to) params.to = to;
      const response = await api.get(`/reports/${selected}/export/`, {
        params,
        responseType: 'blob',
      });
      const url = URL.createObjectURL(
        new Blob([response.data], { type: 'text/csv;charset=utf-8' }),
      );
      const link = document.createElement('a');
      link.href = url;
      link.download = `${selected}-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="page-eyebrow">Management information</span>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">
            Operational and financial reports scoped to your branch and role.
          </p>
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setFrom('');
              setTo('');
            }}
            disabled={!from && !to}
          >
            Reset dates
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={exportCsv}
            disabled={exporting || loading}
          >
            <Download size={16} /> {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {error ? (
        <div className="alert alert-danger">
          <AlertTriangle size={18} /> {error}
        </div>
      ) : null}

      <div className="reports-layout">
        <aside className="content-card report-menu">
          <div className="report-menu-head">
            <BarChart3 size={18} />
            <span>Available reports</span>
          </div>
          {REPORTS.map((report) => {
            const Icon = report.icon;
            return (
              <button
                key={report.key}
                type="button"
                className={`report-menu-item${report.key === selected ? ' active' : ''}`}
                onClick={() => chooseReport(report.key)}
              >
                <Icon size={16} />
                <span>
                  <strong>{report.label}</strong>
                  <small>{report.description}</small>
                </span>
              </button>
            );
          })}
        </aside>

        <section className="report-main">
          <div className="content-card report-filter">
            <div>
              <h2>{definition.label}</h2>
              <p>{definition.description}</p>
            </div>
            <div className="report-dates">
              <label>
                <span>From</span>
                <input
                  type="date"
                  className="input"
                  value={from}
                  onChange={(event) => setFrom(event.target.value)}
                />
              </label>
              <label>
                <span>To</span>
                <input
                  type="date"
                  className="input"
                  value={to}
                  onChange={(event) => setTo(event.target.value)}
                />
              </label>
            </div>
          </div>

          {loading ? (
            <div className="content-card report-loading">
              <span className="spinner spinner-dark" />
              <p>Building report…</p>
            </div>
          ) : null}

          {!loading && statEntries.length > 0 ? (
            <div className="report-summary">
              {statEntries.map(([key, value]) => (
                <div className="summary-card" key={key}>
                  <span>{humanize(key)}</span>
                  <strong>{formatCell(key, value)}</strong>
                </div>
              ))}
            </div>
          ) : null}

          {!loading && validRows.length > 0 ? (
            <section className="content-card mini-section">
              <div className="mini-section-head">
                <h3>Detailed rows</h3>
                <span className="badge badge-neutral">
                  {validRows.length} rows
                </span>
              </div>
              <div className="table-wrap">
                <table className="data-table compact-table">
                  <thead>
                    <tr>
                      {rowColumns.map((column) => (
                        <th key={column}>{humanize(column)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {validRows.map((row, index) => (
                      <tr key={String(row.id ?? row.policy_number ?? index)}>
                        {rowColumns.map((column) => (
                          <td key={column}>{formatCell(column, row[column])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {!loading && reportSections.map(([key, sectionRows]) => (
            <MiniTable key={key} title={key} rows={sectionRows} />
          ))}

          {!loading &&
          validRows.length === 0 &&
          reportSections.length === 0 &&
          statEntries.length === 0 ? (
            <div className="content-card report-loading">
              <p>No data is available for this report and period.</p>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

export default ReportsPage;
