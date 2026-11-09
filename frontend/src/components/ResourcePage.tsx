import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Plus, RefreshCw, Search, X } from 'lucide-react';
import { api, getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import type {
  CollectionAction,
  Paginated,
  ResourceConfig,
  ResourceField,
  ResourceFilter,
  RowAction,
} from '../types';
import { DataTable } from './DataTable';
import { FormField } from './FormField';
import { Modal } from './Modal';
import { invalidateOptionsCache, useRemoteOptions } from '../utils/options';

interface ResourcePageProps {
  config: ResourceConfig;
}

interface Meta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

const EMPTY_META: Meta = { page: 1, pageSize: 20, total: 0, totalPages: 0 };

function FilterSelect({
  filter,
  value,
  onChange,
}: {
  filter: ResourceFilter;
  value: string;
  onChange: (value: string) => void;
}) {
  const remote = useRemoteOptions(
    filter.optionsUrl,
    filter.optionLabel,
    filter.optionValue,
  );
  const options = filter.options ?? remote;
  return (
    <select
      className="input filter-select"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={filter.label}
    >
      <option value="">{filter.label}: All</option>
      {options.map((option) => (
        <option key={String(option.value)} value={String(option.value)}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

function recordLabel(row: Record<string, unknown> | null): string {
  if (!row) return 'this record';
  return String(
    row.name ??
      row.policy_number ??
      row.invoice_number ??
      row.quotation_number ??
      row.claim_number ??
      row.remittance_number ??
      row.note_number ??
      row.receipt_number ??
      row.endorsement_number ??
      row.client_number ??
      row.record_number ??
      row.id ??
      'this record',
  );
}

function initialValuesFor(
  fields: ResourceField[],
  row: Record<string, unknown> | null,
): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.form === false || field.readOnly) continue;
    if (field.type === 'file') {
      values[field.name] = null;
      continue;
    }
    if (row && row[field.name] !== undefined) {
      values[field.name] = row[field.name];
      continue;
    }
    if (field.default !== undefined) {
      values[field.name] = field.default;
    } else if (field.type === 'checkbox') {
      values[field.name] = false;
    } else if (field.type === 'multiselect') {
      values[field.name] = [];
    } else if (
      field.type === 'select' &&
      field.required &&
      field.options?.length
    ) {
      values[field.name] = field.options[0].value;
    } else {
      values[field.name] = '';
    }
  }
  return values;
}

function initialValues(
  config: ResourceConfig,
  row: Record<string, unknown> | null,
): Record<string, unknown> {
  return initialValuesFor(config.fields, row);
}

function validateFields(
  fields: ResourceField[],
  values: Record<string, unknown>,
  isCreate = false,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    const value = values[field.name];
    const empty =
      value === undefined ||
      value === null ||
      value === '' ||
      (Array.isArray(value) && value.length === 0);
    const requiredOnCreate = field.requiredOnCreate && isCreate;
    if ((field.required || requiredOnCreate) && empty) {
      errors[field.name] = `${field.label} is required`;
    }
    if (
      field.type === 'json' &&
      typeof value === 'string' &&
      value.trim() !== ''
    ) {
      try {
        JSON.parse(value);
      } catch {
        errors[field.name] = 'Enter valid JSON';
      }
    }
    if (field.type === 'number' && value !== '' && value !== null && value !== undefined) {
      const num = Number(value);
      if (field.min !== undefined && num < Number(field.min)) {
        errors[field.name] = `${field.label} must be at least ${field.min}`;
      } else if (field.max !== undefined && num > Number(field.max)) {
        errors[field.name] = `${field.label} must be at most ${field.max}`;
      }
    }
  }
  // Cross-field date guards
  const validFrom = values['valid_from'];
  const validTo = values['valid_to'];
  if (validFrom && validTo && String(validTo) <= String(validFrom)) {
    errors['valid_to'] = 'Valid to must be after valid from';
  }
  const startDate = values['start_date'];
  const endDate = values['end_date'];
  if (startDate && endDate && String(endDate) <= String(startDate)) {
    errors['end_date'] = 'End date must be after start date';
  }
  return errors;
}

function buildFieldPayload(
  fields: ResourceField[],
  values: Record<string, unknown>,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const field of fields) {
    const value = values[field.name];
    if (field.name === 'password' && (value === '' || value === null || value === undefined)) {
      continue;
    }
    if (field.type === 'file') {
      if (value instanceof File) payload[field.name] = value;
      continue;
    }
    if (field.type === 'checkbox') {
      payload[field.name] = Boolean(value);
      continue;
    }
    if (field.type === 'multiselect') {
      payload[field.name] = Array.isArray(value) ? value : [];
      continue;
    }
    if (field.type === 'json') {
      if (typeof value === 'string') {
        if (!value.trim()) continue;
        try {
          payload[field.name] = JSON.parse(value);
        } catch {
          payload[field.name] = value;
        }
      } else if (value !== undefined && value !== null) {
        payload[field.name] = value;
      }
      continue;
    }
    if (field.type === 'datetime') {
      if (!value) continue;
      payload[field.name] = new Date(String(value)).toISOString();
      continue;
    }
    if (field.type === 'number') {
      if (value === '' || value === null || value === undefined) continue;
      payload[field.name] = Number(value);
      continue;
    }
    if (value === undefined || value === null || value === '') {
      if (['text', 'email', 'tel', 'textarea'].includes(field.type ?? 'text')) {
        payload[field.name] = '';
      }
      continue;
    }
    payload[field.name] = value;
  }
  return payload;
}

type PendingAction =
  | { kind: 'row'; action: RowAction; row: Record<string, unknown> }
  | { kind: 'collection'; action: CollectionAction };

export function ResourcePage({ config }: ResourcePageProps) {
  const { can } = useAuth();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') ?? '');
  const [debouncedSearch, setDebouncedSearch] = useState(
    searchParams.get('search') ?? '',
  );
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [meta, setMeta] = useState<Meta>(EMPTY_META);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Record<string, unknown> | null>(
    null,
  );
  const [deleting, setDeleting] = useState(false);
  const [busyRowId, setBusyRowId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [actionValues, setActionValues] = useState<Record<string, unknown>>({});
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});
  const [actionError, setActionError] = useState('');
  const [actionSaving, setActionSaving] = useState(false);

  const canView = can(`${config.module}:view`);
  const canCreate =
    !config.noCreate && can(config.createPermission ?? `${config.module}:create`);
  const canEdit =
    !config.noEdit && can(config.editPermission ?? `${config.module}:edit`);
  const canDelete =
    !config.noDelete && can(config.deletePermission ?? `${config.module}:delete`);
  const isCreate = editing === null;

  const activeFields = useMemo(
    () =>
      config.fields.filter(
        (field) =>
          field.form !== false &&
          !field.readOnly &&
          (!field.createOnly || isCreate) &&
          (!field.editOnly || !isCreate),
      ),
    [config.fields, isCreate],
  );

  useEffect(() => {
    const param = searchParams.get('search') ?? '';
    setSearch(param);
    setDebouncedSearch(param);
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 4000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const load = useCallback(async (silent = false) => {
    if (!canView) {
      setLoading(false);
      return;
    }
    if (!silent) setLoading(true);
    setError('');
    const params: Record<string, unknown> = { page, pageSize: 20 };
    if (debouncedSearch) params.search = debouncedSearch;
    for (const [key, value] of Object.entries(filters)) {
      if (value) params[key] = value;
    }
    try {
      const response = await api.get<Paginated<Record<string, unknown>>>(
        config.endpoint,
        { params },
      );
      setRows(response.data.data);
      setMeta(response.data.meta);
    } catch (caught) {
      setError(getErrorMessage(caught));
      setRows([]);
      setMeta(EMPTY_META);
    } finally {
      setLoading(false);
    }
  }, [canView, config.endpoint, debouncedSearch, filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const interval = config.pollInterval ?? 30000;
    if (!interval) return;
    const timer = window.setInterval(() => {
      if (!document.hidden) void load(true);
    }, interval);
    return () => window.clearInterval(timer);
  }, [config.pollInterval, load]);

  const openCreate = () => {
    setEditing(null);
    setValues(initialValues(config, null));
    setFieldErrors({});
    setFormError('');
    setModalOpen(true);
  };

  const openEdit = (row: Record<string, unknown>) => {
    setEditing(row);
    setValues(initialValues(config, row));
    setFieldErrors({});
    setFormError('');
    setModalOpen(true);
  };

  const closeForm = () => {
    if (saving) return;
    setModalOpen(false);
    setEditing(null);
    setFormError('');
  };

  const setValue = (name: string, value: unknown) => {
    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const validate = (): boolean => {
    const errors = validateFields(activeFields, values, isCreate);
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const buildPayload = (): Record<string, unknown> =>
    buildFieldPayload(activeFields, values);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!validate()) return;
    setSaving(true);
    setFormError('');
    const payload = buildPayload();
    const hasFile = activeFields.some(
      (field) => field.type === 'file' && values[field.name] instanceof File,
    );
    try {
      const url = editing
        ? `${config.endpoint}${String(editing.id)}/`
        : config.endpoint;
      const method = editing ? 'patch' : 'post';
      if (hasFile) {
        const formData = new FormData();
        for (const [key, value] of Object.entries(payload)) {
          if (Array.isArray(value)) {
            for (const item of value) formData.append(key, String(item));
          } else if (value !== undefined && value !== null) {
            formData.append(key, value instanceof File ? value : String(value));
          }
        }
        await api.request({
          url,
          method,
          data: formData,
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        await api.request({ url, method, data: payload });
      }
      setModalOpen(false);
      setEditing(null);
      invalidateOptionsCache(config.endpoint);
      setToast(`${config.singular} ${editing ? 'updated' : 'created'} successfully.`);
      await load();
    } catch (caught) {
      setFormError(getErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`${config.endpoint}${String(deleteTarget.id)}/`);
      setDeleteTarget(null);
      setToast(`${config.singular} removed.`);
      await load();
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setDeleting(false);
    }
  };

  const openAction = (pending: PendingAction) => {
    setPendingAction(pending);
    setActionValues(initialValuesFor(pending.action.fields ?? [], pending.kind === 'row' ? pending.row : null));
    setActionErrors({});
    setActionError('');
  };

  const closeAction = () => {
    if (actionSaving) return;
    setPendingAction(null);
    setActionValues({});
    setActionErrors({});
    setActionError('');
  };

  const executeRowAction = async (
    action: RowAction,
    row: Record<string, unknown>,
    extra: Record<string, unknown> = {},
  ) => {
    setBusyRowId(String(row.id ?? ''));
    try {
      const base =
        typeof action.body === 'function' ? action.body(row) : action.body;
      await api.request({
        url: action.url(row),
        method: action.method ?? 'post',
        data: { ...(base ?? {}), ...extra },
      });
      setToast(action.successMessage ?? `${action.label} completed.`);
      await load();
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setBusyRowId(null);
    }
  };

  const runRowAction = (action: RowAction, row: Record<string, unknown>) => {
    if (action.fields?.length) {
      openAction({ kind: 'row', action, row });
      return;
    }
    if (action.confirm && !window.confirm(action.confirm)) return;
    void executeRowAction(action, row);
  };

  const openCollectionAction = (action: CollectionAction) => {
    openAction({ kind: 'collection', action });
  };

  const submitAction = async (event: FormEvent) => {
    event.preventDefault();
    if (!pendingAction) return;
    const fields = pendingAction.action.fields ?? [];
    const errors = validateFields(fields, actionValues);
    setActionErrors(errors);
    if (Object.keys(errors).length > 0) return;
    if (pendingAction.action.confirm && !window.confirm(pendingAction.action.confirm)) {
      return;
    }
    setActionSaving(true);
    setActionError('');
    try {
      const payload = buildFieldPayload(fields, actionValues);
      if (pendingAction.kind === 'row') {
        const { action, row } = pendingAction;
        const base =
          typeof action.body === 'function' ? action.body(row) : action.body;
        setBusyRowId(String(row.id ?? ''));
        try {
          await api.request({
            url: action.url(row),
            method: action.method ?? 'post',
            data: { ...(base ?? {}), ...payload },
          });
        } finally {
          setBusyRowId(null);
        }
        setToast(action.successMessage ?? `${action.label} completed.`);
        await load();
      } else {
        await api.request({
          url: pendingAction.action.url,
          method: pendingAction.action.method ?? 'post',
          data: payload,
        });
        setToast(
          pendingAction.action.successMessage ??
            `${pendingAction.action.label} completed.`,
        );
        await load();
      }
      setPendingAction(null);
      setActionValues({});
    } catch (caught) {
      setActionError(getErrorMessage(caught));
    } finally {
      setActionSaving(false);
    }
  };

  const clearFilters = () => {
    setFilters({});
    setSearch('');
  };

  const activeFilterCount =
    Object.values(filters).filter(Boolean).length + (search ? 1 : 0);

  if (!canView) {
    return (
      <div className="page">
        <div className="empty-state">
          <AlertCircle size={32} />
          <h2>Access restricted</h2>
          <p>You do not have permission to view {config.title.toLowerCase()}.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="page-eyebrow">{config.group}</span>
          <h1 className="page-title">{config.title}</h1>
          {config.description ? (
            <p className="page-subtitle">{config.description}</p>
          ) : null}
        </div>
        <div className="page-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => load()}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spin' : undefined} />
            Refresh
          </button>
          {(config.collectionActions ?? [])
            .filter((action) => !action.permission || can(action.permission))
            .map((action) => (
              <button
                key={action.label}
                type="button"
                className={`btn btn-${
                  action.variant === 'danger'
                    ? 'danger'
                    : action.variant === 'success'
                      ? 'primary'
                      : 'ghost'
                }`}
                onClick={() => openCollectionAction(action)}
              >
                <Plus size={16} /> {action.label}
              </button>
            ))}
          {canCreate ? (
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              <Plus size={16} /> New {config.singular.toLowerCase()}
            </button>
          ) : null}
        </div>
      </div>

      {toast ? (
        <div className="alert alert-success">
          <CheckCircle2 size={18} /> {toast}
        </div>
      ) : null}
      {error ? (
        <div className="alert alert-danger">
          <AlertCircle size={18} /> {error}
        </div>
      ) : null}

      <div className="toolbar">
        <div className="toolbar-search">
          <Search size={17} />
          <input
            type="search"
            value={search}
            placeholder={config.searchPlaceholder ?? `Search ${config.title.toLowerCase()}…`}
            onChange={(event) => setSearch(event.target.value)}
            aria-label={`Search ${config.title}`}
          />
        </div>
        <div className="toolbar-filters">
          {(config.filters ?? []).map((filter) => (
            <FilterSelect
              key={filter.name}
              filter={filter}
              value={filters[filter.name] ?? ''}
              onChange={(value) => {
                setFilters((current) => ({ ...current, [filter.name]: value }));
                setPage(1);
              }}
            />
          ))}
          {activeFilterCount > 0 ? (
            <button type="button" className="btn btn-ghost btn-sm" onClick={clearFilters}>
              <X size={14} /> Clear
            </button>
          ) : null}
        </div>
      </div>

      <DataTable
        fields={config.fields}
        rows={rows}
        loading={loading}
        page={meta.page}
        pageSize={meta.pageSize || 20}
        total={meta.total}
        totalPages={meta.totalPages}
        onPageChange={setPage}
        onEdit={canEdit ? openEdit : undefined}
        onDelete={canDelete ? setDeleteTarget : undefined}
        canEdit={canEdit}
        canDelete={canDelete}
        rowActions={config.rowActions}
        can={can}
        onRowAction={runRowAction}
        busyRowId={busyRowId}
        detailPath={config.detailPath}
        emptyMessage={
          activeFilterCount > 0
            ? 'No records match your search or filters.'
            : `No ${config.title.toLowerCase()} yet.`
        }
      />

      <Modal
        open={modalOpen}
        title={`${isCreate ? 'New' : 'Edit'} ${config.singular.toLowerCase()}`}
        subtitle={config.description}
        onClose={closeForm}
        size="wide"
        footer={
          <>
            <button type="button" className="btn btn-ghost" onClick={closeForm} disabled={saving}>
              Cancel
            </button>
            <button type="submit" form="resource-form" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : isCreate ? `Create ${config.singular.toLowerCase()}` : 'Save changes'}
            </button>
          </>
        }
      >
        <form id="resource-form" className="form-grid" onSubmit={submit} noValidate>
          {formError ? (
            <div className="alert alert-danger form-alert">
              <AlertCircle size={18} /> {formError}
            </div>
          ) : null}
          {activeFields.map((field: ResourceField) => (
            <FormField
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={(value) => setValue(field.name, value)}
              error={fieldErrors[field.name]}
              disabled={saving}
              isCreate={isCreate}
            />
          ))}
          {activeFields.length === 0 ? (
            <p className="muted">No editable fields are available for this record.</p>
          ) : null}
        </form>
      </Modal>

      <Modal
        open={Boolean(pendingAction)}
        title={
          pendingAction?.kind === 'row'
            ? pendingAction.action.fieldsTitle ?? pendingAction.action.label
            : pendingAction?.action.label ?? 'Action'
        }
        subtitle={
          pendingAction?.kind === 'row'
            ? pendingAction.action.fieldsDescription
            : pendingAction?.action.description
        }
        onClose={closeAction}
        size="wide"
        footer={
          <>
            <button type="button" className="btn btn-ghost" onClick={closeAction} disabled={actionSaving}>
              Cancel
            </button>
            <button type="submit" form="action-form" className="btn btn-primary" disabled={actionSaving}>
              {actionSaving ? 'Working…' : pendingAction?.action.label ?? 'Continue'}
            </button>
          </>
        }
      >
        <form id="action-form" className="form-grid" onSubmit={submitAction} noValidate>
          {actionError ? (
            <div className="alert alert-danger form-alert">
              <AlertCircle size={18} /> {actionError}
            </div>
          ) : null}
          {(pendingAction?.action.fields ?? []).map((field) => (
            <FormField
              key={field.name}
              field={field}
              value={actionValues[field.name]}
              onChange={(value) => {
                setActionValues((current) => ({ ...current, [field.name]: value }));
                setActionErrors((current) => {
                  if (!current[field.name]) return current;
                  const next = { ...current };
                  delete next[field.name];
                  return next;
                });
              }}
              error={actionErrors[field.name]}
              disabled={actionSaving}
            />
          ))}
        </form>
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        title={`Remove ${config.singular.toLowerCase()}?`}
        onClose={() => (deleting ? undefined : setDeleteTarget(null))}
        footer={
          <>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setDeleteTarget(null)}
              disabled={deleting}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={confirmDelete}
              disabled={deleting}
            >
              {deleting ? 'Removing…' : 'Remove'}
            </button>
          </>
        }
      >
        <p>
          You are about to remove <strong>{recordLabel(deleteTarget)}</strong>. This
          action is audited and may deactivate rather than permanently delete the
          record.
        </p>
      </Modal>
    </div>
  );
}
