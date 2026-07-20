/**
 * ABYSS Design Tokens - Typography
 * Technical monospace + clean sans-serif combination
 */

export const typography = {
  fontFamilies: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: 'JetBrains Mono, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
    display: 'Space Grotesk, Inter, system-ui, sans-serif',
  },

  fontSizes: {
    xs: '0.75rem',     // 12px
    sm: '0.875rem',    // 14px
    base: '1rem',      // 16px
    lg: '1.125rem',    // 18px
    xl: '1.25rem',     // 20px
    '2xl': '1.5rem',   // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem',  // 36px
    '5xl': '3rem',     // 48px
    '6xl': '3.75rem',  // 60px
  } as const,

  fontWeights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  } as const,

  lineHeights: {
    tight: 1.1,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  } as const,

  letterSpacings: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  } as const,
} as const;

export type FontFamily = keyof typeof typography.fontFamilies;
export type FontSize = keyof typeof typography.fontSizes;
export type FontWeight = keyof typeof typography.fontWeights;
export type LineHeight = keyof typeof typography.lineHeights;
export type LetterSpacing = keyof typeof typography.letterSpacings;

// Semantic typography presets
export const textStyles = {
  // Display
  display: {
    fontFamily: 'display',
    fontSize: '4xl',
    fontWeight: 'bold',
    lineHeight: 'tight',
    letterSpacing: 'tight',
  },
  displayLg: {
    fontFamily: 'display',
    fontSize: '5xl',
    fontWeight: 'extrabold',
    lineHeight: 'tight',
    letterSpacing: 'tight',
  },
  displaySm: {
    fontFamily: 'display',
    fontSize: '3xl',
    fontWeight: 'bold',
    lineHeight: 'tight',
  },

  // Headings
  h1: {
    fontFamily: 'display',
    fontSize: '3xl',
    fontWeight: 'bold',
    lineHeight: 'tight',
  },
  h2: {
    fontFamily: 'display',
    fontSize: '2xl',
    fontWeight: 'semibold',
    lineHeight: 'snug',
  },
  h3: {
    fontFamily: 'display',
    fontSize: 'xl',
    fontWeight: 'semibold',
    lineHeight: 'snug',
  },
  h4: {
    fontFamily: 'sans',
    fontSize: 'lg',
    fontWeight: 'semibold',
    lineHeight: 'normal',
  },
  h5: {
    fontFamily: 'sans',
    fontSize: 'base',
    fontWeight: 'semibold',
    lineHeight: 'normal',
  },
  h6: {
    fontFamily: 'sans',
    fontSize: 'sm',
    fontWeight: 'semibold',
    lineHeight: 'normal',
    textTransform: 'uppercase',
    letterSpacing: 'wide',
  },

  // Body
  bodyLg: {
    fontFamily: 'sans',
    fontSize: 'lg',
    lineHeight: 'relaxed',
  },
  body: {
    fontFamily: 'sans',
    fontSize: 'base',
    lineHeight: 'normal',
  },
  bodySm: {
    fontFamily: 'sans',
    fontSize: 'sm',
    lineHeight: 'normal',
  },
  bodyXs: {
    fontFamily: 'sans',
    fontSize: 'xs',
    lineHeight: 'normal',
  },

  // Monospace
  monoLg: {
    fontFamily: 'mono',
    fontSize: 'lg',
    lineHeight: 'normal',
  },
  mono: {
    fontFamily: 'mono',
    fontSize: 'base',
    lineHeight: 'normal',
  },
  monoSm: {
    fontFamily: 'mono',
    fontSize: 'sm',
    lineHeight: 'normal',
  },
  monoXs: {
    fontFamily: 'mono',
    fontSize: 'xs',
    lineHeight: 'normal',
  },

  // UI
  label: {
    fontFamily: 'sans',
    fontSize: 'sm',
    fontWeight: 'medium',
    lineHeight: 'normal',
    textTransform: 'uppercase' as const,
    letterSpacing: 'wide',
  },
  labelSm: {
    fontFamily: 'sans',
    fontSize: 'xs',
    fontWeight: 'medium',
    lineHeight: 'normal',
    textTransform: 'uppercase' as const,
    letterSpacing: 'wider',
  },
  button: {
    fontFamily: 'sans',
    fontSize: 'sm',
    fontWeight: 'semibold',
    lineHeight: 'normal',
  },
  buttonLg: {
    fontFamily: 'sans',
    fontSize: 'base',
    fontWeight: 'semibold',
    lineHeight: 'normal',
  },
  caption: {
    fontFamily: 'sans',
    fontSize: 'xs',
    lineHeight: 'normal',
    color: 'fg.tertiary',
  },
  code: {
    fontFamily: 'mono',
    fontSize: 'sm',
    lineHeight: 'normal',
  },
} as const;

export type TextStyle = keyof typeof textStyles;