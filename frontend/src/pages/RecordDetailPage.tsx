import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, FileText, MessageSquare, RefreshCw } from 'lucide-react';
import { api, getErrorMessage } from '../api/client';
import type { Paginated, ResourceConfig } from '../types';
import { formatValue, statusTone, titleCase } from '../utils/format';

interface RecordDetailPageProps {
  config: ResourceConfig;
}

interface DocumentRow {
  id: string;
  name: string;
  category?: string;
  file_name?: string;
  file_url?: string;
  version?: number;
  created_at?: string;
}

interface CommunicationRow {
  id: string;
  channel: string;
  subject?: string;
  message?: string;
  status?: string;
  sent_at?: string;
}

function recordTitle(data: Record<string, unknown> | null): string {
  if (!data) return 'Record';
  return String(
    data.name ??
      data.policy_number ??
      data.quotation_number ??
      data.claim_number ??
      data.invoice_number ??
      data.client_number ??
      data.id ??
      'Record',
  );
}

export function RecordDetailPage({ config }: RecordDetailPageProps) {
  const { id } = useParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [communications, setCommunications] = useState<CommunicationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const response = await api.get(`${config.endpoint}${id}/`);
        if (cancelled) return;
        setData(response.data.data as Record<string, unknown>);
        const entityType = config.detailEntityType;
        if (!entityType) return;
        const [documentResponse, communicationResponse] = await Promise.all([
          api.get<Paginated<DocumentRow>>('/documents/', {
            params: { entity_type: entityType, entity_id: id, pageSize: 100 },
          }),
          api.get<Paginated<CommunicationRow>>('/communications/', {
            params: { related_entity_id: id, pageSize: 100 },
          }),
        ]);
        if (cancelled) return;
        setDocuments(documentResponse.data.data);
        setCommunications(communicationResponse.data.data);
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
  }, [config.detailEntityType, config.endpoint, id]);

  const displayFields = useMemo(
    () =>
      config.fields.filter(
        (field) =>
          field.name !== 'password' &&
          field.name !== 'file' &&
          field.name !== 'file_url',
      ),
    [config.fields],
  );

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link className="back-link" to={config.path}>
            <ArrowLeft size={16} /> Back to {config.title}
          </Link>
          <span className="page-eyebrow">{config.group}</span>
          <h1 className="page-title">
            {loading ? `Loading ${config.singular.toLowerCase()}…` : recordTitle(data)}
          </h1>
          <p className="page-subtitle">{config.description}</p>
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="alert alert-danger">
          <AlertCircle size={18} /> {error}
        </div>
      ) : null}

      {loading ? (
        <div className="content-card report-loading">
          <span className="spinner spinner-dark" />
          <p>Loading record…</p>
        </div>
      ) : null}

      {!loading && data ? (
        <>
          <section className="content-card detail-card">
            <div className="mini-section-head">
              <h3>Overview</h3>
              {typeof data.status === 'string' ? (
                <span className={`badge badge-${statusTone(data.status)}`}>
                  {titleCase(data.status)}
                </span>
              ) : null}
            </div>
            <dl className="detail-list">
              {displayFields.map((field) => (
                <div key={field.name}>
                  <dt>{field.label}</dt>
                  <dd>
                    {field.linkTo && data[field.name] !== undefined ? (
                      <a
                        className="table-link"
                        href={field.linkTo(data)}
                        target={field.external ? '_blank' : undefined}
                        rel={field.external ? 'noreferrer' : undefined}
                      >
                        {formatValue(data[field.name], field.format)}
                      </a>
                    ) : (
                      formatValue(data[field.name], field.format)
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <div className="detail-columns">
            <section className="content-card">
              <div className="mini-section-head">
                <h3><FileText size={18} /> Documents</h3>
                <span className="badge badge-neutral">{documents.length}</span>
              </div>
              {documents.length === 0 ? (
                <p className="muted">No documents are attached to this record.</p>
              ) : (
                <div className="detail-links">
                  {documents.map((document) => (
                    <a
                      key={document.id}
                      className="detail-link"
                      href={document.file_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <FileText size={16} />
                      <span>
                        <strong>{document.name}</strong>
                        <small>
                          {document.category || 'Document'} · v{document.version ?? 1}
                        </small>
                      </span>
                    </a>
                  ))}
                </div>
              )}
              <Link className="btn btn-ghost btn-sm" to="/documents">
                Manage documents
              </Link>
            </section>

            <section className="content-card">
              <div className="mini-section-head">
                <h3><MessageSquare size={18} /> Communications</h3>
                <span className="badge badge-neutral">{communications.length}</span>
              </div>
              {communications.length === 0 ? (
                <p className="muted">No communications are linked to this record.</p>
              ) : (
                <div className="detail-links">
                  {communications.map((communication) => (
                    <div key={communication.id} className="detail-link">
                      <MessageSquare size={16} />
                      <span>
                        <strong>{communication.subject || communication.channel}</strong>
                        <small>
                          {communication.channel} · {titleCase(communication.status)}
                          {communication.sent_at ? ` · ${formatValue(communication.sent_at, 'datetime')}` : ''}
                        </small>
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <Link className="btn btn-ghost btn-sm" to="/communications">
                Manage communications
              </Link>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default RecordDetailPage;
