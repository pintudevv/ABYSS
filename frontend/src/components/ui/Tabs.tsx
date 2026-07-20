'use client';

import React, { forwardRef, HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export interface TabsProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> {
  defaultValue?: string;
  onChange?: (value: string) => void;
  children: React.ReactNode;
}

const TabsContext = React.createContext<{ value: string; onChange: (value: string) => void } | null>(null);

export const Tabs = forwardRef<HTMLDivElement, TabsProps>(
  ({ defaultValue, onChange, children, className, ...props }, ref) => {
    const [value, setValue] = React.useState(defaultValue || '');

    const handleChange = (newValue: string) => {
      setValue(newValue);
      onChange?.(newValue);
    };

    return (
      <TabsContext.Provider value={{ value, onChange: handleChange }}>
        <div ref={ref} className={clsx('w-full', className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    )
  }
);

Tabs.displayName = 'Tabs';

export const TabsList = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        'flex gap-1 p-1 rounded-xl bg-slate-900/50 border border-white/10',
        className
      )}
      role="tablist"
      {...props}
    >
      {children}
    </div>
  )
);
TabsList.displayName = 'TabsList';

export interface TabsTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  value: string;
}

export const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ value, className, children, ...props }, ref) => {
    const context = React.useContext(TabsContext);
    const isActive = context?.value === value;

    return (
      <button
        ref={ref}
        role="tab"
        aria-selected={isActive}
        className={clsx(
          'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50',
          isActive
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
            : 'text-slate-400 hover:text-white hover:bg-white/5',
          className
        )}
        onClick={() => context?.onChange(value)}
        {...props}
      >
        {children}
      </button>
    )
  }
);

TabsTrigger.displayName = 'TabsTrigger';

export const TabsContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { value: string }>(
  ({ value, className, children, ...props }, ref) => {
    const context = React.useContext(TabsContext);
    const isActive = context?.value === value;

    if (!isActive) return null;

    return (
      <div
        ref={ref}
        role="tabpanel"
        className={clsx('mt-4 animate-fade-in', className)}
        {...props}
      >
        {children}
      </div>
    )
  }
);

TabsContent.displayName = 'TabsContent';