import { useId, type InputHTMLAttributes } from "react";
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
