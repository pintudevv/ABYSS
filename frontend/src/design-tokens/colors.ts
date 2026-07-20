/**
 * ABYSS Design Tokens - Colors
 * Cyber-security themed color palette with light/dark modes
 */

export const colors = {
  // Base semantic colors (used by both themes)
  semantic: {
    background: {
      primary: { light: '#ffffff', dark: '#050508' },
      secondary: { light: '#f8fafc', dark: '#0d0d14' },
      tertiary: { light: '#f1f5f9', dark: '#1a1a2e' },
      inverted: { light: '#050508', dark: '#ffffff' },
    },
    foreground: {
      primary: { light: '#0f172a', dark: '#f3f4f6' },
      secondary: { light: '#475569', dark: '#9ca3af' },
      tertiary: { light: '#94a3b8', dark: '#6b7280' },
      inverted: { light: '#ffffff', dark: '#050508' },
      disabled: { light: '#cbd5e1', dark: '#4b5563' },
    },
    border: {
      primary: { light: '#e2e8f0', dark: '#1e1e2e' },
      secondary: { light: '#cbd5e1', dark: '#2d2d44' },
      focus: { light: '#6366f1', dark: '#818cf8' },
      error: { light: '#ef4444', dark: '#f87171' },
      success: { light: '#22c55e', dark: '#4ade80' },
      warning: { light: '#f59e0b', dark: '#fbbf24' },
    },
    brand: {
      indigo: { light: '#4f46e5', dark: '#6366f1' },
      indigoLight: { light: '#818cf8', dark: '#a5b4fc' },
      indigoDark: { light: '#3730a3', dark: '#4338ca' },
    },
    status: {
      critical: { light: '#dc2626', dark: '#ef4444' },
      high: { light: '#ea580c', dark: '#f97316' },
      medium: { light: '#d97706', dark: '#fbbf24' },
      low: { light: '#2563eb', dark: '#60a5fa' },
      info: { light: '#0891b2', dark: '#22d3ee' },
      success: { light: '#16a34a', dark: '#22c55e' },
    },
    glass: {
      background: { light: 'rgba(255, 255, 255, 0.03)', dark: 'rgba(255, 255, 255, 0.03)' },
      border: { light: 'rgba(255, 255, 255, 0.06)', dark: 'rgba(255, 255, 255, 0.06)' },
      highlight: { light: 'rgba(255, 255, 255, 0.1)', dark: 'rgba(255, 255, 255, 0.1)' },
    },
    overlay: {
      backdrop: { light: 'rgba(15, 23, 42, 0.6)', dark: 'rgba(5, 5, 8, 0.8)' },
      modal: { light: 'rgba(255, 255, 255, 0.95)', dark: 'rgba(13, 13, 20, 0.95)' },
    },
  },

  // Gradient presets
  gradients: {
    brand: {
      primary: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
      secondary: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
      subtle: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
    },
    status: {
      critical: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
      success: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
      warning: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    },
    surface: {
      glass: 'linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%)',
      card: 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
    },
  },

  // Shadow presets
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
    glow: {
      indigo: '0 0 20px rgba(99, 102, 241, 0.3), 0 0 40px rgba(99, 102, 241, 0.1)',
      red: '0 0 20px rgba(239, 68, 68, 0.3), 0 0 40px rgba(239, 68, 68, 0.1)',
      green: '0 0 20px rgba(34, 197, 94, 0.3), 0 0 40px rgba(34, 197, 94, 0.1)',
      amber: '0 0 20px rgba(245, 158, 11, 0.3), 0 0 40px rgba(245, 158, 11, 0.1)',
    },
    card: '0 20px 50px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
  },
};

export type ColorToken = keyof typeof colors.semantic.background.primary;