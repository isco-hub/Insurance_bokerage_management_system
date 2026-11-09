import { ChevronLeft, ChevronRight, Eye, Pencil, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { ResourceField, RowAction } from '../types';
import { formatValue, statusTone, titleCase } from '../utils/format';

interface DataTableProps {
  fields: ResourceField[];
  rows: Record<string, unknown>[];
  loading: boolean;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onEdit?: (row: Record<string, unknown>) => void;
  onDelete?: (row: Record<string, unknown>) => void;
  canEdit?: boolean;
  canDelete?: boolean;
  rowActions?: RowAction[];
  can: (code: string) => boolean;
  onRowAction?: (action: RowAction, row: Record<string, unknown>) => void;
  busyRowId?: string | null;
  emptyMessage?: string;
  detailPath?: (row: Record<string, unknown>) => string;
}

function isStatusField(field: ResourceField): boolean {
  return (
    field.name === 'status' ||
    field.name === 'priority' ||
    field.name === 'kyc_status' ||
    field.name.endsWith('_status')
  );
}

export function DataTable({
  fields,
  rows,
  loading,
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onEdit,
  onDelete,
  canEdit,
  canDelete,
  rowActions = [],
  can,
  onRowAction,
  busyRowId,
  emptyMessage = 'No records found.',
  detailPath,
}: DataTableProps) {
  const columns = fields.filter((field) => field.table);
  const visibleActions = rowActions.filter(
    (action) => !action.permission || can(action.permission),
  );
  const hasActions =
    Boolean(onEdit && canEdit) ||
    Boolean(onDelete && canDelete) ||
    visibleActions.length > 0;
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="content-card table-card">
      <div className="table-wrap">
        <table className="data-table" data-loading={loading}>
          <thead>
            <tr>
              {columns.map((field) => (
                <th key={field.name} style={field.width ? { width: field.width } : undefined}>
                  {field.label}
                </th>
              ))}
              {hasActions ? <th className="actions-head">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td className="table-empty" colSpan={columns.length + (hasActions ? 1 : 0)}>
                  <span className="spinner spinner-dark" /> Loading records…
                </td>
              </tr>
            ) : null}
            {!loading && rows.length === 0 ? (
              <tr>
                <td className="table-empty" colSpan={columns.length + (hasActions ? 1 : 0)}>
                  {emptyMessage}
                </td>
              </tr>
            ) : null}
            {rows.map((row) => {
              const rowId = String(row.id ?? '');
              const busy = busyRowId === rowId;
              const actions = visibleActions.filter(
                (action) => !action.show || action.show(row),
              );
              return (
                <tr key={rowId} data-busy={busy}>
                  {columns.map((field) => {
                    const value = row[field.name];
                    return (
                      <td key={field.name}>
                        {field.render ? (
                          field.render(row)
                        ) : field.linkTo ? (
                          field.external ? (
                            <a
                              className="table-link"
                              href={field.linkTo(row)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {formatValue(value, field.format)}
                            </a>
                          ) : (
                            <Link className="table-link" to={field.linkTo(row)}>
                              {formatValue(value, field.format)}
                            </Link>
                          )
                        ) : isStatusField(field) ? (
                          <span className={`badge badge-${statusTone(value)}`}>
                            {titleCase(value)}
                          </span>
                        ) : (
                          formatValue(value, field.format)
                        )}
                      </td>
                    );
                  })}
                  {hasActions ? (
                    <td className="actions-cell">
                      <div className="row-actions">
                        {actions.map((action) => (
                          <button
                            key={action.label}
                            type="button"
                            className={`row-action row-action-${action.variant ?? 'default'}`}
                            onClick={() => onRowAction?.(action, row)}
                            disabled={busy}
                          >
                            {action.label}
                          </button>
                        ))}
                        {detailPath ? (
                          <Link
                            className="icon-btn"
                            title="View details"
                            aria-label="View record details"
                            to={detailPath(row)}
                          >
                            <Eye size={16} />
                          </Link>
                        ) : null}
                        {onEdit && canEdit ? (
                          <button
                            type="button"
                            className="icon-btn"
                            title="Edit"
                            aria-label="Edit record"
                            onClick={() => onEdit(row)}
                            disabled={busy}
                          >
                            <Pencil size={16} />
                          </button>
                        ) : null}
                        {onDelete && canDelete ? (
                          <button
                            type="button"
                            className="icon-btn icon-btn-danger"
                            title="Delete"
                            aria-label="Delete record"
                            onClick={() => onDelete(row)}
                            disabled={busy}
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : null}
                      </div>
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span className="page-info">
          Showing {from}–{to} of {total}
        </span>
        <div className="pagination-buttons">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
          >
            <ChevronLeft size={16} /> Previous
          </button>
          <span className="page-count">
            Page {totalPages === 0 ? 0 : page} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
