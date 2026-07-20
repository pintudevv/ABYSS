export const shadows = {
  // Elevation levels (0-5)
  elevation: {
    0: 'none',
    1: '0 1px 2px rgba(0, 0, 0, 0.05), 0 1px 1px rgba(0, 0, 0, 0.04)',
    2: '0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.06)',
    3: '0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
    4: '0 20px 25px rgba(0, 0, 0, 0.15), 0 10px 10px rgba(0, 0, 0, 0.04)',
    5: '0 25px 50px rgba(0, 0, 0, 0.25), 0 15px 15px rgba(0, 0, 0, 0.05)',
  },

  // Colored glow shadows
  glow: {
    primary: '0 0 20px rgba(99, 102, 241, 0.3), 0 0 40px rgba(99, 102, 241, 0.1)',
    success: '0 0 20px rgba(0, 255, 136, 0.3), 0 0 40px rgba(0, 255, 136, 0.1)',
    danger: '0 0 20px rgba(255, 51, 102, 0.3), 0 0 40px rgba(255, 51, 102, 0.1)',
    warning: '0 0 20px rgba(255, 170, 0, 0.3), 0 0 40px rgba(255, 170, 0, 0.1)',
    cyan: '0 0 20px rgba(34, 211, 238, 0.3), 0 0 40px rgba(34, 211, 238, 0.1)',
  },

  // Inner shadows
  inner: {
    subtle: 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',
    medium: 'inset 0 4px 8px rgba(0, 0, 0, 0.1)',
    strong: 'inset 0 8px 16px rgba(0, 0, 0, 0.15)',
  },

  // Focus rings
  focus: {
    default: '0 0 0 2px rgba(99, 102, 241, 0.4)',
    success: '0 0 0 2px rgba(0, 255, 136, 0.4)',
    danger: '0 0 0 2px rgba(255, 51, 102, 0.4)',
    warning: '0 0 0 2px rgba(255, 170, 0, 0.4)',
  },

  // Glassmorphism
  glass: {
    subtle: '0 4px 30px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
    medium: '0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
    strong: '0 20px 50px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
  },
} as const;

export type ShadowToken = keyof typeof shadows.elevation | keyof typeof shadows.glow;