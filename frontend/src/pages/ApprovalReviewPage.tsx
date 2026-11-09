import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  ExternalLink,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { api, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import {
  formatValue,
  statusTone,
  titleCase,
} from '../utils/format';

interface Approval {
  id: string;
  type: string;
  entity_type: string;
  entity_id: string;
  amount?: number | string | null;
  requested_by?: string;
  requested_by_name?: string;
  approver_name?: string;
  status: string;
  comments?: string;
  requested_at?: string;
  decided_at?: string;
}

interface ReviewPayload {
  approval: Approval;
  entity: Record<string, unknown> | null;
  entity_available: boolean;
}

const ENTITY_LINKS: Record<string, string> = {
  client: '/clients',
  insurer: '/insurers',
  quotation: '/quotations',
  policy: '/policies',
  claim: '/claims',
};

function isDateKey(key: string) {
  return (
    key.endsWith('_at') ||
    key.endsWith('_date') ||
    ['date', 'from', 'to', 'period_from', 'period_to'].includes(key)
  );
}

function isCurrencyKey(key: string) {
  return /(amount|premium|tax|total|balance|reserve|rate|commission)/.test(key);
}

function EntityValue({ field, value }: { field: string; value: unknown }) {
  if (value === null || value === undefined || value === '') {
    return <>—</>;
  }
  if (Array.isArray(value)) {
    return <>{value.length} item{value.length === 1 ? '' : 's'}</>;
  }
  if (typeof value === 'object') {
    return <>{JSON.stringify(value)}</>;
  }
  if (isDateKey(field)) {
    return <>{formatValue(value, String(value).includes('T') ? 'datetime' : 'date')}</>;
  }
  if (isCurrencyKey(field) && !Number.isNaN(Number(value))) {
    return <>{formatValue(value, 'currency')}</>;
  }
  return <>{formatValue(value)}</>;
}

export function ApprovalReviewPage() {
  const { id } = useParams();
  const { user, can } = useAuth();
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.get(`/approvals/${id}/review/`);
      const data = response.data.data as ReviewPayload;
      setPayload(data);
      setComments(data.approval.comments ?? '');
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (status: 'APPROVED' | 'REJECTED') => {
    if (!payload) return;
    if (status === 'REJECTED' && !comments.trim()) {
      setError('A rejection reason is required.');
      return;
    }
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await api.post(`/approvals/${payload.approval.id}/decide/`, {
        status,
        comments,
      });
      setMessage(`Request ${status.toLowerCase()}.`);
      await load();
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const approval = payload?.approval;
  const entityFields = useMemo(() => {
    if (!payload?.entity) return [];
    return Object.entries(payload.entity).filter(
      ([key, value]) =>
        key !== 'id' &&
        (value === null ||
          value === undefined ||
          typeof value !== 'object' ||
          Array.isArray(value)),
    );
  }, [payload]);
  const entityHref = approval
    ? `${ENTITY_LINKS[approval.entity_type.toLowerCase()] ?? ''}/${approval.entity_id}`
    : '';
  const canDecide =
    Boolean(approval) &&
    approval?.status === 'PENDING' &&
    can('approvals:approve') &&
    approval?.requested_by !== user?.id;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link className="back-link" to="/approvals">
            <ArrowLeft size={16} /> Back to Approvals
          </Link>
          <span className="page-eyebrow">Management review</span>
          <h1 className="page-title">
            {loading ? 'Loading approval…' : `${titleCase(approval?.type)} review`}
          </h1>
          <p className="page-subtitle">
            Review the request together with the linked transaction before deciding.
          </p>
        </div>
        <div className="page-actions">
          <button type="button" className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="alert alert-danger">
          <AlertCircle size={18} /> {error}
        </div>
      ) : null}
      {message ? (
        <div className="alert alert-success">
          <CheckCircle2 size={18} /> {message}
        </div>
      ) : null}

      {loading ? (
        <div className="content-card report-loading">
          <span className="spinner spinner-dark" />
          <p>Loading approval review…</p>
        </div>
      ) : null}

      {!loading && approval ? (
        <div className="approval-review">
          <section className="content-card detail-card">
            <div className="mini-section-head">
              <h3><ClipboardCheck size={18} /> Request</h3>
              <span className={`badge badge-${statusTone(approval.status)}`}>
                {titleCase(approval.status)}
              </span>
            </div>
            <dl className="detail-list">
              <div>
                <dt>Approval type</dt>
                <dd>{titleCase(approval.type)}</dd>
              </div>
              <div>
                <dt>Amount</dt>
                <dd>
                  {approval.amount === null || approval.amount === undefined
                    ? '—'
                    : formatValue(approval.amount, 'currency')}
                </dd>
              </div>
              <div>
                <dt>Requested by</dt>
                <dd>{approval.requested_by_name || '—'}</dd>
              </div>
              <div>
                <dt>Requested at</dt>
                <dd>{formatValue(approval.requested_at, 'datetime')}</dd>
              </div>
              <div>
                <dt>Decision by</dt>
                <dd>{approval.approver_name || '—'}</dd>
              </div>
              <div>
                <dt>Decided at</dt>
                <dd>{formatValue(approval.decided_at, 'datetime')}</dd>
              </div>
              <div>
                <dt>Comments</dt>
                <dd>{approval.comments || '—'}</dd>
              </div>
            </dl>
          </section>

          <section className="content-card detail-card">
            <div className="mini-section-head">
              <h3>Linked {titleCase(approval.entity_type)}</h3>
              {approval.entity_id && ENTITY_LINKS[approval.entity_type.toLowerCase()] ? (
                <Link className="table-link" to={entityHref}>
                  Open record <ExternalLink size={14} />
                </Link>
              ) : null}
            </div>
            {!payload?.entity_available ? (
              <p className="muted">
                The linked record is no longer available. Review the request details
                above before deciding.
              </p>
            ) : (
              <dl className="detail-list">
                {entityFields.map(([field, value]) => (
                  <div key={field}>
                    <dt>{titleCase(field)}</dt>
                    <dd>
                      <EntityValue field={field} value={value} />
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          {canDecide ? (
            <section className="content-card detail-card">
              <div className="mini-section-head">
                <h3>Decision</h3>
              </div>
              <div className="form-field full">
                <label className="field-label" htmlFor="approval-comments">
                  Review comments
                </label>
                <textarea
                  id="approval-comments"
                  className="input textarea"
                  rows={4}
                  value={comments}
                  onChange={(event) => setComments(event.target.value)}
                  placeholder="Record conditions, notes or the rejection reason."
                />
              </div>
              <div className="approval-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => decide('APPROVED')}
                  disabled={busy}
                >
                  <CheckCircle2 size={16} /> Approve request
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => decide('REJECTED')}
                  disabled={busy}
                >
                  <XCircle size={16} /> Reject request
                </button>
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default ApprovalReviewPage;
