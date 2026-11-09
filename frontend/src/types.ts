import type { ReactNode } from 'react';

export interface User {
  id: string;
  employee_no?: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone?: string;
  role?: string;
  role_name?: string;
  role_code?: string;
  branch?: string;
  branch_name?: string;
  is_active: boolean;
  must_change_password?: boolean;
  last_login_at?: string;
  permissions: string[];
}

export interface Paginated<T> {
  data: T[];
  meta: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

export interface ApiError {
  statusCode?: number;
  message?: string;
  details?: unknown;
}

export type FieldType =
  | 'text'
  | 'email'
  | 'tel'
  | 'number'
  | 'date'
  | 'datetime'
  | 'select'
  | 'multiselect'
  | 'textarea'
  | 'checkbox'
  | 'file'
  | 'json';

export interface Option {
  label: string;
  value: string | number;
}

export interface ResourceField {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  requiredOnCreate?: boolean;
  options?: Option[];
  optionsUrl?: string;
  optionLabel?: string | ((item: Record<string, unknown>) => string);
  optionValue?: string;
  table?: boolean;
  form?: boolean;
  readOnly?: boolean;
  createOnly?: boolean;
  editOnly?: boolean;
  width?: string;
  placeholder?: string;
  help?: string;
  step?: string;
  min?: string;
  max?: string;
  default?: unknown;
  format?: 'currency' | 'date' | 'datetime' | 'boolean' | 'number';
  render?: (row: Record<string, unknown>) => ReactNode;
  linkTo?: (row: Record<string, unknown>) => string;
  external?: boolean;
}

export interface ResourceFilter {
  name: string;
  label: string;
  options?: Option[];
  optionsUrl?: string;
  optionLabel?: string;
  optionValue?: string;
}

export interface RowAction {
  label: string;
  permission?: string;
  method?: 'post' | 'patch' | 'delete';
  url: (row: Record<string, unknown>) => string;
  body?: Record<string, unknown> | ((row: Record<string, unknown>) => Record<string, unknown>);
  confirm?: string;
  show?: (row: Record<string, unknown>) => boolean;
  variant?: 'default' | 'danger' | 'success';
  fields?: ResourceField[];
  fieldsTitle?: string;
  fieldsDescription?: string;
  successMessage?: string;
}

export interface CollectionAction {
  label: string;
  permission?: string;
  method?: 'post' | 'patch';
  url: string;
  fields: ResourceField[];
  confirm?: string;
  variant?: 'default' | 'danger' | 'success';
  successMessage?: string;
  description?: string;
}

export interface ResourceConfig {
  key: string;
  path: string;
  title: string;
  singular: string;
  module: string;
  endpoint: string;
  group: string;
  description?: string;
  searchPlaceholder?: string;
  fields: ResourceField[];
  filters?: ResourceFilter[];
  rowActions?: RowAction[];
  collectionActions?: CollectionAction[];
  detailPath?: (row: Record<string, unknown>) => string;
  detailEntityType?: string;
  pollInterval?: number;
  createPermission?: string;
  editPermission?: string;
  deletePermission?: string;
  noCreate?: boolean;
  noEdit?: boolean;
  noDelete?: boolean;
}
