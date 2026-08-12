"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "danger";
type ButtonSize = "sm" | "md" | "lg" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
};

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-gold text-white hover:bg-gold-soft active:bg-ink disabled:opacity-40",
  secondary:
    "border border-border bg-surface text-ink hover:border-gold/50 hover:text-gold active:bg-gold-tint disabled:opacity-40",
  danger:
    "bg-danger text-white hover:bg-danger-hover active:bg-danger-hover disabled:opacity-40",
};

// size="md" (44px) là ngưỡng tối thiểu WCAG cho touch target trên mobile
// cư dân dùng; size="sm" (36px) chỉ dành cho control phụ trên desktop BQL.
const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-9 px-3.5 text-xs gap-1.5",
  md: "h-11 px-5 text-sm gap-2",
  lg: "h-12 px-6 text-sm gap-2",
  icon: "h-11 w-11 shrink-0",
};

export default function Button({
  variant = "primary",
  size = "md",
  fullWidth,
  loading,
  leftIcon,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-xl font-medium transition disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 shrink-0 animate-spin" /> : leftIcon}
      {children}
    </button>
  );
}
