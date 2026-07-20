// Design Tokens - Central Export
// ================================
// All design tokens in one place for easy importing

// Colors
export * from './colors';

// Typography
export * from './typography';

// Spacing
export * from './spacing';

// Radii
export * from './radii';

// Transitions
export * from './transitions';

// Shadows
export * from './shadows';

// Breakpoints
export * from './breakpoints';

// Z-Index
export * from './z-index';

// ============================================================
// CSS Variable Definitions (for :root / [data-theme])
// ============================================================

export const cssVars = {
  // Colors
  color: {
    // Background
    bgPrimary: '--color-bg-primary',
    bgSecondary: '--color-bg-secondary',
    bgTertiary: '--color-bg-tertiary',
    bgHover: '--color-bg-hover',
    bgActive: '--color-bg-active',

    // Foreground
    fgPrimary: '--color-fg-primary',
    fgSecondary: '--color-fg-secondary',
    fgMuted: '--color-fg-muted',
    fgInverse: '--color-fg-inverse',

    // Accents
    accentPrimary: '--color-accent-primary',
    accentSuccess: '--color-accent-success',
    accentDanger: '--color-accent-danger',
    accentWarning: '--color-accent-warning',
    accentCyan: '--color-accent-cyan',

    // Borders
    borderSubtle: '--color-border-subtle',
    borderEmphasis: '--color-border-emphasis',
    borderFocus: '--color-border-focus',
  },

  // Typography
  typography: {
    fontSans: '--font-sans',
    fontMono: '--font-mono',
    fontDisplay: '--font-display',

    fontSizeXs: '--font-size-xs',
    fontSizeSm: '--font-size-sm',
    fontSizeBase: '--font-size-base',
    fontSizeLg: '--font-size-lg',
    fontSizeXl: '--font-size-xl',
    fontSize2xl: '--font-size-2xl',
    fontSize3xl: '--font-size-3xl',
    fontSize4xl: '--font-size-4xl',

    fontWeightNormal: '--font-weight-normal',
    fontWeightMedium: '--font-weight-medium',
    fontWeightSemibold: '--font-weight-semibold',
    fontWeightBold: '--font-weight-bold',

    lineHeightTight: '--line-height-tight',
    lineHeightNormal: '--line-height-normal',
    lineHeightRelaxed: '--line-height-relaxed',
  },

  // Spacing
  spacing: {
    0: '--space-0',
    1: '--space-1',
    2: '--space-2',
    3: '--space-3',
    4: '--space-4',
    5: '--space-5',
    6: '--space-6',
    8: '--space-8',
    10: '--space-10',
    12: '--space-12',
    16: '--space-16',
    20: '--space-20',
    24: '--space-24',
    32: '--space-32',
  },

  // Radii
  radius: {
    none: '--radius-none',
    sm: '--radius-sm',
    md: '--radius-md',
    lg: '--radius-lg',
    xl: '--radius-xl',
    '2xl': '--radius-2xl',
    '3xl': '--radius-3xl',
    full: '--radius-full',
  },

  // Shadows
  shadow: {
    elevation1: '--shadow-elevation-1',
    elevation2: '--shadow-elevation-2',
    elevation3: '--shadow-elevation-3',
    elevation4: '--shadow-elevation-4',
    elevation5: '--shadow-elevation-5',
    glowPrimary: '--shadow-glow-primary',
    glowSuccess: '--shadow-glow-success',
    glowDanger: '--shadow-glow-danger',
    focus: '--shadow-focus',
    glass: '--shadow-glass-medium',
  },

  // Transitions
  transition: {
    durationFast: '--duration-fast',
    durationNormal: '--duration-normal',
    durationSlow: '--duration-slow',
    easingEaseOut: '--easing-ease-out',
    easingSpring: '--easing-spring',
    easingSnappy: '--easing-snappy',
  },

  // Breakpoints
  breakpoint: {
    xs: '--breakpoint-xs',
    sm: '--breakpoint-sm',
    md: '--breakpoint-md',
    lg: '--breakpoint-lg',
    xl: '--breakpoint-xl',
    '2xl': '--breakpoint-2xl',
  },

  // Z-Index
  zIndex: {
    base: '--z-base',
    dropdown: '--z-dropdown',
    sticky: '--z-sticky',
    fixed: '--z-fixed',
    modalBackdrop: '--z-modal-backdrop',
    modal: '--z-modal',
    popover: '--z-popover',
    tooltip: '--z-tooltip',
    toast: '--z-toast',
    loading: '--z-loading',
  },
} as const;

// ============================================================
// Theme Config Generator
// ============================================================

export function generateThemeCSSVars(theme: 'light' | 'dark'): Record<string, string> {
  const themes = {
    light: {
      '--color-bg-primary': '#ffffff',
      '--color-bg-secondary': '#f8fafc',
      '--color-bg-tertiary': '#f1f5f9',
      '--color-bg-hover': '#e2e8f0',
      '--color-bg-active': '#cbd5e1',
      '--color-fg-primary': '#0f172a',
      '--color-fg-secondary': '#475569',
      '--color-fg-muted': '#94a3b8',
      '--color-fg-inverse': '#ffffff',
      '--color-accent-primary': '#4f46e5',
      '--color-accent-success': '#059669',
      '--color-accent-danger': '#dc2626',
      '--color-accent-warning': '#d97706',
      '--color-accent-cyan': '#06b6d4',
      '--color-border-subtle': 'rgba(15, 23, 42, 0.08)',
      '--color-border-emphasis': 'rgba(15, 23, 42, 0.16)',
      '--color-border-focus': 'rgba(79, 70, 229, 0.4)',

      '--shadow-glass-medium': '0 8px 32px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
    },
    dark: {
      '--color-bg-primary': '#050508',
      '--color-bg-secondary': '#0a0a12',
      '--color-bg-tertiary': '#12121a',
      '--color-bg-hover': '#1e1e2e',
      '--color-bg-active': '#2a2a3e',
      '--color-fg-primary': '#f3f4f6',
      '--color-fg-secondary': '#94a3b8',
      '--color-fg-muted': '#64748b',
      '--color-fg-inverse': '#050508',
      '--color-accent-primary': '#6366f1',
      '--color-accent-success': '#00ff88',
      '--color-accent-danger': '#ff3366',
      '--color-accent-warning': '#ffaa00',
      '--color-accent-cyan': '#22d3ee',
      '--color-border-subtle': 'rgba(255, 255, 255, 0.06)',
      '--color-border-emphasis': 'rgba(255, 255, 255, 0.12)',
      '--color-border-focus': 'rgba(99, 102, 241, 0.4)',

      '--shadow-glass-medium': '0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
    },
  };

  return themes[theme];
}

// ============================================================
// Complete CSS Variable String for :root
// ============================================================

export function getAllCSSVars(theme: 'light' | 'dark' = 'dark'): string {
  const vars = generateThemeCSSVars(theme);

  // Common vars (same for both themes)
  const common = {
    // Typography
    '--font-sans': 'Inter, system-ui, sans-serif',
    '--font-mono': 'JetBrains Mono, Menlo, monospace',
    '--font-display': 'Space Grotesk, Inter, sans-serif',

    '--font-size-xs': '0.75rem',
    '--font-size-sm': '0.875rem',
    '--font-size-base': '1rem',
    '--font-size-lg': '1.125rem',
    '--font-size-xl': '1.25rem',
    '--font-size-2xl': '1.5rem',
    '--font-size-3xl': '2rem',
    '--font-size-4xl': '2.5rem',

    '--font-weight-normal': '400',
    '--font-weight-medium': '500',
    '--font-weight-semibold': '600',
    '--font-weight-bold': '700',

    '--line-height-tight': '1.1',
    '--line-height-normal': '1.5',
    '--line-height-relaxed': '1.75',

    // Spacing
    '--space-0': '0',
    '--space-1': '0.25rem',
    '--space-2': '0.5rem',
    '--space-3': '0.75rem',
    '--space-4': '1rem',
    '--space-5': '1.25rem',
    '--space-6': '1.5rem',
    '--space-8': '2rem',
    '--space-10': '2.5rem',
    '--space-12': '3rem',
    '--space-16': '4rem',
    '--space-20': '5rem',
    '--space-24': '6rem',
    '--space-32': '8rem',

    // Radii
    '--radius-none': '0',
    '--radius-sm': '0.25rem',
    '--radius-md': '0.375rem',
    '--radius-lg': '0.5rem',
    '--radius-xl': '0.75rem',
    '--radius-2xl': '1rem',
    '--radius-3xl': '1.5rem',
    '--radius-full': '9999px',

    // Shadows
    '--shadow-elevation-1': '0 1px 2px rgba(0, 0, 0, 0.05), 0 1px 1px rgba(0, 0, 0, 0.04)',
    '--shadow-elevation-2': '0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.06)',
    '--shadow-elevation-3': '0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
    '--shadow-elevation-4': '0 20px 25px rgba(0, 0, 0, 0.15), 0 10px 10px rgba(0, 0, 0, 0.04)',
    '--shadow-elevation-5': '0 25px 50px rgba(0, 0, 0, 0.25), 0 15px 15px rgba(0, 0, 0, 0.05)',

    '--shadow-glow-primary': '0 0 20px rgba(99, 102, 241, 0.3), 0 0 40px rgba(99, 102, 241, 0.1)',
    '--shadow-glow-success': '0 0 20px rgba(0, 255, 136, 0.3), 0 0 40px rgba(0, 255, 136, 0.1)',
    '--shadow-glow-danger': '0 0 20px rgba(255, 51, 102, 0.3), 0 0 40px rgba(255, 51, 102, 0.1)',

    '--shadow-focus': '0 0 0 2px rgba(99, 102, 241, 0.4)',
    '--shadow-glass-medium': '0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08)',

    // Transitions
    '--duration-fast': '150ms',
    '--duration-normal': '250ms',
    '--duration-slow': '350ms',
    '--easing-ease-out': 'cubic-bezier(0, 0, 0.2, 1)',
    '--easing-spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
    '--easing-snappy': 'cubic-bezier(0.2, 0, 0, 1)',

    // Breakpoints
    '--breakpoint-xs': '320px',
    '--breakpoint-sm': '640px',
    '--breakpoint-md': '768px',
    '--breakpoint-lg': '1024px',
    '--breakpoint-xl': '1280px',
    '--breakpoint-2xl': '1536px',

    // Z-Index
    '--z-base': '0',
    '--z-dropdown': '100',
    '--z-sticky': '200',
    '--z-fixed': '300',
    '--z-modal-backdrop': '400',
    '--z-modal': '500',
    '--z-popover': '600',
    '--z-tooltip': '700',
    '--z-toast': '1000',
    '--z-loading': '2000',
  };

  const allVars = { ...vars, ...common };
  return Object.entries(allVars)
    .map(([key, value]) => `${key}: ${value};`)
    .join('\n');
}