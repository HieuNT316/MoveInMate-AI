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
    "bg-gradient-to-r from-gold to-gold-soft text-white shadow-[0_10px_22px_-12px_rgba(0,86,210,0.8)] hover:-translate-y-0.5 hover:shadow-[0_14px_28px_-14px_rgba(0,86,210,0.85)] active:translate-y-0 active:bg-ink disabled:opacity-40",
  secondary:
    "border border-border bg-surface/90 text-ink shadow-sm hover:-translate-y-0.5 hover:border-gold/50 hover:text-gold hover:shadow-md active:translate-y-0 active:bg-gold-tint disabled:opacity-40",
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
      className={`inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:transform-none ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 shrink-0 animate-spin" /> : leftIcon}
      {children}
    </button>
  );
}
