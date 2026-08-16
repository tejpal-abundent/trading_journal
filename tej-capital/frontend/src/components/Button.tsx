import type { ButtonHTMLAttributes } from "react";
import clsx from "clsx";
import "../design/components.css";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

export function Button({ variant = "primary", className, type = "button", ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={clsx("btn", `btn--${variant}`, className)}
      {...rest}
    />
  );
}
