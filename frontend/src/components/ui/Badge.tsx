'use client';

import React, { forwardRef, HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
}

const variantStyles = {
  default: 'bg-slate-800/50 text-slate-300 border border-slate-600/50',
  success: 'bg-emerald-900/30 text-emerald-400 border border-emerald-500/30',
  danger: 'bg-red-900/30 text-red-400 border border-red-500/30',
  warning: 'bg-amber-900/30 text-amber-400 border border-amber-500/30',
  info: 'bg-indigo-900/30 text-indigo-400 border border-indigo-500/30',
  neutral: 'bg-slate-800/50 text-slate-400 border border-slate-600/50',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-[10px] gap-1',
  md: 'px-2.5 py-1 text-[11px] gap-1.5',
  lg: 'px-3 py-1.5 text-sm gap-2',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'default', size = 'md', dot = false, className, children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center justify-center font-medium rounded-full border transition-colors',
          'font-mono',
          sizeStyles[size],
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {dot && <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" aria-hidden="true" />}
        {children}
      </span>
    )
  }
);

Badge.displayName = 'Badge';