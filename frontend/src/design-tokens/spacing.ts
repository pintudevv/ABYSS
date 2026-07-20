/**
 * ABYSS Design Tokens - Spacing
 * Consistent spacing scale based on 4px base unit
 */

export const spacing = {
  // Base unit: 4px
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  7: '1.75rem',   // 28px
  8: '2rem',      // 32px
  9: '2.25rem',   // 36px
  10: '2.5rem',   // 40px
  11: '2.75rem',  // 44px
  12: '3rem',     // 48px
  14: '3.5rem',   // 56px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  28: '7rem',     // 112px
  32: '8rem',     // 128px
} as const;

export const space = spacing;

export type SpacingToken = keyof typeof spacing;

// Semantic spacing aliases
export const semanticSpacing = {
  // Component internal spacing
  xs: spacing[1],     // 4px - tight
  sm: spacing[2],     // 8px - compact
  md: spacing[4],     // 16px - default
  lg: spacing[6],     // 24px - comfortable
  xl: spacing[8],     // 32px - spacious
  '2xl': spacing[12], // 48px - section
  '3xl': spacing[16], // 64px - major section

  // Layout spacing
  container: spacing[6],    // 24px - page padding
  section: spacing[12],     // 48px - section gap
  component: spacing[4],    // 16px - component gap
  inline: spacing[2],       // 8px - inline gap
  stack: spacing[4],        // 16px - vertical stack
} as const;

export type SemanticSpacing = keyof typeof semanticSpacing;