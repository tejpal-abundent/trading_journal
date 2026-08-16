import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import clsx from "clsx";
import "../design/components.css";

export type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  helperText?: string;
};

export function TextField({ label, error, helperText, className, id, ...rest }: TextFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className="field">
      <label htmlFor={fieldId} className="field__label">
        {label}
      </label>
      <input
        id={fieldId}
        className={clsx("field__input", error && "field__input--error", className)}
        aria-invalid={!!error}
        {...rest}
      />
      {error ? (
        <p className="field__error">{error}</p>
      ) : helperText ? (
        <p className="field__helper">{helperText}</p>
      ) : null}
    </div>
  );
}

export type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  error?: string;
  helperText?: string;
  children: ReactNode;
};

export function SelectField({ label, error, helperText, className, id, children, ...rest }: SelectFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className="field">
      <label htmlFor={fieldId} className="field__label">
        {label}
      </label>
      <select
        id={fieldId}
        className={clsx("field__input", error && "field__input--error", className)}
        aria-invalid={!!error}
        {...rest}
      >
        {children}
      </select>
      {error ? (
        <p className="field__error">{error}</p>
      ) : helperText ? (
        <p className="field__helper">{helperText}</p>
      ) : null}
    </div>
  );
}

export type TextareaFieldProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
  helperText?: string;
};

export function TextareaField({ label, error, helperText, className, id, ...rest }: TextareaFieldProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className="field">
      <label htmlFor={fieldId} className="field__label">
        {label}
      </label>
      <textarea
        id={fieldId}
        className={clsx("field__input", "field__input--textarea", error && "field__input--error", className)}
        aria-invalid={!!error}
        {...rest}
      />
      {error ? (
        <p className="field__error">{error}</p>
      ) : helperText ? (
        <p className="field__helper">{helperText}</p>
      ) : null}
    </div>
  );
}
