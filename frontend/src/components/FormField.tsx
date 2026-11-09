import { useId } from 'react';
import type { ChangeEvent, ReactNode } from 'react';
import type { ResourceField } from '../types';
import { useRemoteOptions } from '../utils/options';
import { toDateTimeLocal } from '../utils/format';

interface FormFieldProps {
  field: ResourceField;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
  disabled?: boolean;
  isCreate?: boolean;
}

export function FormField({
  field,
  value,
  onChange,
  error,
  disabled,
  isCreate = false,
}: FormFieldProps) {
  const id = useId();
  const remoteOptions = useRemoteOptions(
    field.optionsUrl,
    field.optionLabel,
    field.optionValue,
  );
  const options = field.options ?? remoteOptions;
  const type = field.type ?? 'text';
  const inputId = `field-${field.name}-${id}`;
  const errorId = `${inputId}-error`;

  const handleInput = (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    onChange(event.target.value);
  };

  let control: ReactNode;

  if (type === 'textarea' || type === 'json') {
    control = (
      <textarea
        id={inputId}
        className="input textarea"
        rows={type === 'json' ? 4 : 3}
        value={
          type === 'json' && value && typeof value === 'object'
            ? JSON.stringify(value, null, 2)
            : String(value ?? '')
        }
        placeholder={field.placeholder}
        onChange={handleInput}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />
    );
  } else if (type === 'select') {
    control = (
      <select
        id={inputId}
        className="input select"
        value={String(value ?? '')}
        onChange={handleInput}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      >
        <option value="">Select…</option>
        {options.map((option) => (
          <option key={String(option.value)} value={String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else if (type === 'multiselect') {
    const selected = Array.isArray(value) ? value.map(String) : [];
    control = (
      <select
        id={inputId}
        className="input select multiselect"
        multiple
        size={Math.min(Math.max(options.length, 4), 10)}
        value={selected}
        onChange={(event) =>
          onChange(
            Array.from(event.target.selectedOptions, (option) => option.value),
          )
        }
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      >
        {options.map((option) => (
          <option key={String(option.value)} value={String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else if (type === 'checkbox') {
    control = (
      <label className="checkbox-control">
        <input
          id={inputId}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
          disabled={disabled}
        />
        <span>{field.help ?? `Enable ${field.label.toLowerCase()}`}</span>
      </label>
    );
  } else if (type === 'file') {
    control = (
      <input
        id={inputId}
        type="file"
        className="input file-input"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />
    );
  } else {
    const htmlType = type === 'datetime' ? 'datetime-local' : type;
    control = (
      <input
        id={inputId}
        type={htmlType}
        className="input"
        value={
          type === 'datetime'
            ? toDateTimeLocal(value)
            : String(value ?? '')
        }
        placeholder={field.placeholder}
        step={field.step}
        min={field.min}
        max={field.max}
        onChange={handleInput}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />
    );
  }

  return (
    <div className={`form-field${type === 'textarea' || type === 'json' || type === 'multiselect' ? ' full' : ''}`}>
      <label className="field-label" htmlFor={inputId}>
        {field.label}
        {field.required || (field.requiredOnCreate && isCreate) ? (
          <span className="required-mark"> *</span>
        ) : null}
      </label>
      {control}
      {field.help && type !== 'checkbox' ? (
        <span className="field-help">{field.help}</span>
      ) : null}
      {error ? (
        <span className="field-error" id={errorId}>
          {error}
        </span>
      ) : null}
    </div>
  );
}
