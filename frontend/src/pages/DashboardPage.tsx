import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Clock,
  Coins,
  HeartPulse,
  Percent,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Users,
  Wallet,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { StatCard } from '../components/StatCard';
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  statusTone,
  titleCase,
} from '../utils/format';

interface Kpis {
  active_clients: number;
  active_policies: number;
  total_policies: number;
  premium_placed_ytd: number;
  brokerage_earned_ytd: number;
  outstanding_premium: number;
  outstanding_commission: number;
  open_claims: number;
  renewals_due_90: number;
  new_business_month: number;
  pending_approvals: number;
  overdue_tasks: number;
  claims_reserve: number;
}

interface ChartPoint {
  name?: string;
  month?: string;
  status?: string;
  count: number;
  premium?: number;
  reserve?: number;
  paid?: number;
}

interface DashboardData {
  kpis: Kpis;
  charts: {
    policies_by_class: ChartPoint[];
    business_by_insurer: ChartPoint[];
    business_by_broker: ChartPoint[];
    premium_by_month: ChartPoint[];
    claims_by_status: ChartPoint[];
    renewal_pipeline: ChartPoint[];
  };
  renewals_due: Record<string, unknown>[];
  tasks_due: Record<string, unknown>[];
  recent_activity: {
    id: string;
    action: string;
    module: string;
    description: string;
    user: string;
    created_at: string;
  }[];
}

const COLORS = ['#1d7a8c', '#2f506f', '#e6a23c', '#c0574f', '#7a6fae', '#4c956c', '#6b7f96'];

function monthLabel(month: string): string {
  if (!month) return '';
  const [year, value] = month.split('-');
  const date = new Date(Number(year), Number(value) - 1, 1);
  return date.toLocaleDateString('en-GB', { month: 'short' });
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const response = await api.get('/dashboard/');
        if (!cancelled) setData(response.data.data as DashboardData);
      } catch (caught) {
        if (!cancelled) setError(getErrorMessage(caught));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="page page-loading">
        <span className="spinner spinner-dark" />
        <p>Loading dashboard…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <div className="alert alert-danger">
          <AlertTriangle size={18} /> {error || 'Unable to load the dashboard.'}
        </div>
      </div>
    );
  }

  const { kpis, charts, renewals_due, tasks_due, recent_activity } = data;
  const premiumByMonth = charts.premium_by_month.map((point) => ({
    ...point,
    label: monthLabel(point.month ?? ''),
  }));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="page-eyebrow">
            {new Date().toLocaleDateString('en-GB', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </span>
          <h1 className="page-title">
            {greeting()}, {user?.first_name ?? 'there'}.
          </h1>
          <p className="page-subtitle">
            Here is the current position of your brokerage across clients,
            premiums, renewals and claims.
          </p>
        </div>
        <div className="page-actions">
          <Link to="/reports" className="btn btn-ghost">
            <BarChart3 size={16} /> Open reports
          </Link>
          <Link to="/policies" className="btn btn-primary">
            <ShieldCheck size={16} /> View policies
          </Link>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Active clients"
          value={kpis.active_clients}
          hint={`${kpis.new_business_month} new policies this month`}
          icon={Users}
          tone="navy"
        />
        <StatCard
          label="Active policies"
          value={kpis.active_policies}
          hint={`${kpis.total_policies} total policies`}
          icon={ShieldCheck}
          tone="teal"
        />
        <StatCard
          label="Premium placed YTD"
          value={formatCurrency(kpis.premium_placed_ytd, true)}
          hint="Total premium written this year"
          icon={TrendingUp}
          tone="violet"
        />
        <StatCard
          label="Brokerage earned YTD"
          value={formatCurrency(kpis.brokerage_earned_ytd, true)}
          hint="Commission recognised this year"
          icon={Percent}
          tone="teal"
        />
        <StatCard
          label="Outstanding premium"
          value={formatCurrency(kpis.outstanding_premium, true)}
          hint={`${formatCurrency(kpis.outstanding_commission, true)} commission due`}
          icon={Wallet}
          tone="amber"
        />
        <StatCard
          label="Open claims"
          value={kpis.open_claims}
          hint={`${formatCurrency(kpis.claims_reserve, true)} reserves held`}
          icon={HeartPulse}
          tone="rose"
        />
        <StatCard
          label="Renewals due (90 days)"
          value={kpis.renewals_due_90}
          hint="Policies approaching renewal"
          icon={RefreshCw}
          tone="slate"
        />
        <StatCard
          label="Pending approvals"
          value={kpis.pending_approvals}
          hint={`${kpis.overdue_tasks} overdue tasks`}
          icon={BadgeCheck}
          tone="violet"
        />
      </div>

      <div className="dashboard-grid">
        <section className="content-card chart-card chart-wide">
          <div className="chart-head">
            <div>
              <h2>Premium production</h2>
              <p>Premium placed by month this year</p>
            </div>
            <span className="badge badge-info">{new Date().getFullYear()}</span>
          </div>
          <div className="chart-body">
            {premiumByMonth.length === 0 ? (
              <p className="empty-state-inline">No premium written in the current year yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={premiumByMonth} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="premiumFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#1d7a8c" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#1d7a8c" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ef" vertical={false} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis
                    tickFormatter={(value) => formatCurrency(value, true)}
                    tickLine={false}
                    axisLine={false}
                    width={80}
                  />
                  <Tooltip
                    formatter={(value) => formatCurrency(Number(value))}
                    labelFormatter={(label) => `${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="premium"
                    name="Premium"
                    stroke="#1d7a8c"
                    strokeWidth={2}
                    fill="url(#premiumFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="content-card chart-card">
          <div className="chart-head">
            <div>
              <h2>Policies by class</h2>
              <p>Distribution of business</p>
            </div>
          </div>
          <div className="chart-body">
            {charts.policies_by_class.length === 0 ? (
              <p className="empty-state-inline">No policies to display.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={charts.policies_by_class}
                    dataKey="count"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={2}
                  >
                    {charts.policies_by_class.map((entry, index) => (
                      <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `${value} policies`} />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="content-card chart-card chart-wide">
          <div className="chart-head">
            <div>
              <h2>Business by insurer</h2>
              <p>Premium placed per insurance partner</p>
            </div>
          </div>
          <div className="chart-body">
            {charts.business_by_insurer.length === 0 ? (
              <p className="empty-state-inline">No insurer production to display.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={charts.business_by_insurer.slice(0, 6)}
                  layout="vertical"
                  margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ef" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(value) => formatCurrency(value, true)}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={120}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Bar dataKey="premium" name="Premium" fill="#2f506f" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="content-card chart-card">
          <div className="chart-head">
            <div>
              <h2>Claims position</h2>
              <p>Open claims by status</p>
            </div>
          </div>
          <div className="chart-body claim-list">
            {charts.claims_by_status.length === 0 ? (
              <p className="empty-state-inline">No claims recorded.</p>
            ) : (
              charts.claims_by_status.map((claim) => (
                <div className="claim-line" key={claim.status}>
                  <span className={`badge badge-${statusTone(claim.status)}`}>
                    {titleCase(claim.status)}
                  </span>
                  <span className="claim-count">{claim.count}</span>
                  <span className="claim-amount">
                    {formatCurrency(claim.reserve ?? 0, true)} reserve
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="content-card chart-card chart-wide">
          <div className="chart-head">
            <div>
              <h2>Renewals due</h2>
              <p>Next policies approaching renewal</p>
            </div>
            <Link to="/renewals" className="text-link">
              View all
            </Link>
          </div>
          <div className="chart-body table-wrap">
            <table className="data-table compact-table">
              <thead>
                <tr>
                  <th>Policy</th>
                  <th>Client</th>
                  <th>Due date</th>
                  <th>Days</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {renewals_due.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="table-empty">
                      No renewals due in the next 90 days.
                    </td>
                  </tr>
                ) : (
                  renewals_due.map((renewal) => (
                    <tr key={String(renewal.id)}>
                      <td>
                        <Link
                          className="text-link"
                          to={`/renewals?search=${encodeURIComponent(String(renewal.policy_number ?? ''))}`}
                        >
                          {String(renewal.policy_number ?? '—')}
                        </Link>
                      </td>
                      <td>{String(renewal.client_name ?? '—')}</td>
                      <td>{formatDate(renewal.due_date)}</td>
                      <td>{String(renewal.days_to_due ?? '—')}</td>
                      <td>
                        <span className={`badge badge-${statusTone(renewal.status)}`}>
                          {titleCase(renewal.status)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="content-card chart-card">
          <div className="chart-head">
            <div>
              <h2>Tasks due</h2>
              <p>Your team&apos;s follow-ups</p>
            </div>
            <Link to="/tasks" className="text-link">
              View all
            </Link>
          </div>
          <div className="chart-body task-list">
            {tasks_due.length === 0 ? (
              <p className="empty-state-inline">No open tasks. Nice work.</p>
            ) : (
              tasks_due.map((task) => (
                <div className="task-line" key={String(task.id)}>
                  <div>
                    <strong>{String(task.title ?? 'Untitled task')}</strong>
                    <span>
                      {String(task.assigned_to_name ?? 'Unassigned')} ·{' '}
                      {formatDate(task.due_date)}
                    </span>
                  </div>
                  <span className={`badge badge-${statusTone(task.priority)}`}>
                    {titleCase(task.priority)}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="content-card chart-card chart-wide">
          <div className="chart-head">
            <div>
              <h2>Recent activity</h2>
              <p>Latest actions across the system</p>
            </div>
            <Activity size={18} className="muted-icon" />
          </div>
          <div className="chart-body activity-list">
            {recent_activity.length === 0 ? (
              <p className="empty-state-inline">No activity recorded.</p>
            ) : (
              recent_activity.map((log) => (
                <div className="activity-line" key={log.id}>
                  <span className="activity-dot" />
                  <div>
                    <strong>{log.description || `${titleCase(log.action)} ${log.module}`}</strong>
                    <span>
                      {log.user || 'System'} · {formatDateTime(log.created_at)}
                    </span>
                  </div>
                  <span className={`badge badge-${statusTone(log.action)}`}>
                    {titleCase(log.action)}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="content-card chart-card">
          <div className="chart-head">
            <div>
              <h2>Renewal pipeline</h2>
              <p>Current renewal stages</p>
            </div>
            <Clock size={18} className="muted-icon" />
          </div>
          <div className="chart-body claim-list">
            {charts.renewal_pipeline.length === 0 ? (
              <p className="empty-state-inline">No renewals tracked yet.</p>
            ) : (
              charts.renewal_pipeline.map((point) => (
                <div className="claim-line" key={point.status}>
                  <span className={`badge badge-${statusTone(point.status)}`}>
                    {titleCase(point.status)}
                  </span>
                  <span className="claim-count">{point.count}</span>
                  <span className="claim-amount">renewals</span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="dashboard-note">
        <Coins size={16} />
        <span>
          Reporting is scoped automatically to your branch and permissions.
          Figures refresh each time you open the dashboard.
        </span>
      </div>
    </div>
  );
}

export default DashboardPage;
