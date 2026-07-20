'use client';

import React, { ReactNode } from 'react';
import { ThemeProvider } from '@/src/hooks/useTheme';
import { ToastProvider } from '@/src/components/ui/Toast';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider defaultTheme="system">
      <ToastProvider>
        {children}
      </ToastProvider>
    </ThemeProvider>
  );
}