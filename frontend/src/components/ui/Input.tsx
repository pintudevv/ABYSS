'use client';

import React, { forwardRef, InputHTMLAttributes } from 'react';
import { clsx } from 'clsx';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'prefix' | 'suffix'> {
  label?: string;
  error?: string;
  hint?: string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, prefix, suffix, className, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-slate-300 mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {prefix && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              {prefix}
            </div>
          )}
          <input
            id={inputId}
            className={clsx(
              'w-full rounded-xl bg-slate-900/50 border transition-all duration-200',
              'text-white placeholder-slate-500',
              'placeholder:text-slate-600',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'bg-slate-900/50 border-slate-700/50 hover:border-slate-600/50',
              'focus:border-indigo-500 focus:ring-indigo-500/30',
              error && 'border-red-500/50 focus:ring-red-500/30',
              'text-sm px-4 py-2.5 rounded-xl transition-all duration-200',
              'pr-10',
              className
            )}
            ref={ref}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            {...props}
          />
          {suffix && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400">
              {suffix}
            </div>
          )}
        </div>
        {error && (
          <p id={`${inputId}-error`} className="mt-1.5 text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="mt-1.5 text-sm text-slate-500">
            {hint}
          </p>
        )}
      </div>
    )
  }
);

Input.displayName = 'Input';