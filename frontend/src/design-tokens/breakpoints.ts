export const breakpoints = {
  // Mobile-first breakpoints
  xs: '320px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',

  // Named aliases
  mobile: '640px',
  tablet: '768px',
  desktop: '1024px',
  wide: '1280px',
  ultrawide: '1536px',

  // Container max widths
  container: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1400px',
  },
} as const;

export type BreakpointToken = keyof typeof breakpoints;

export const mediaQueries = {
  xs: `(min-width: ${breakpoints.xs})`,
  sm: `(min-width: ${breakpoints.sm})`,
  md: `(min-width: ${breakpoints.md})`,
  lg: `(min-width: ${breakpoints.lg})`,
  xl: `(min-width: ${breakpoints.xl})`,
  '2xl': `(min-width: ${breakpoints['2xl']})`,

  // Max-width queries
  'max-xs': `(max-width: ${Number(breakpoints.xs.replace('px', '')) - 1}px)`,
  'max-sm': `(max-width: ${Number(breakpoints.sm.replace('px', '')) - 1}px)`,
  'max-md': `(max-width: ${Number(breakpoints.md.replace('px', '')) - 1}px)`,
  'max-lg': `(max-width: ${Number(breakpoints.lg.replace('px', '')) - 1}px)`,
  'max-xl': `(max-width: ${Number(breakpoints.xl.replace('px', '')) - 1}px)`,

  // Range queries
  mobile: `(max-width: ${Number(breakpoints.sm.replace('px', '')) - 1}px)`,
  tablet: `(min-width: ${breakpoints.sm}) and (max-width: ${Number(breakpoints.lg.replace('px', '')) - 1}px)`,
  desktop: `(min-width: ${breakpoints.lg})`,
} as const;

export type MediaQueryToken = keyof typeof mediaQueries;