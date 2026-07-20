export const zIndex = {
  // Base layers
  base: 0,
  hide: -1,

  // Layout
  dropdown: 100,
  sticky: 200,
  fixed: 300,

  // Overlays
  modalBackdrop: 400,
  modal: 500,
  popover: 600,
  tooltip: 700,

  // Toast notifications
  toast: 1000,

  // Critical
  loading: 2000,
} as const;

export type ZIndexToken = keyof typeof zIndex;

// CSS custom property names
export const zIndexCssVars = {
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
} as const;