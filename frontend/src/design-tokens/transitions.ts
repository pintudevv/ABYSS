/**
 * ABYSS Design Tokens - Transitions
 */

import { radii } from './radii';

export const transitions = {
  // Durations
  duration: {
    instant: '0ms',
    fast: '150ms',
    normal: '250ms',
    slow: '350ms',
    slower: '500ms',
  },

  // Easing curves
  easing: {
    linear: 'linear',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    // Apple-style spring
    spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
    // Snappy
    snappy: 'cubic-bezier(0.2, 0, 0, 1)',
    // Bounce
    bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },

  // Preset combinations
  presets: {
    fast: '150ms easeOut',
    normal: '250ms easeOut',
    slow: '350ms easeInOut',
    spring: '400ms spring',
    snappy: '200ms snappy',
  },
} as const;

export type RadiusToken = keyof typeof radii;
export type DurationToken = keyof typeof transitions.duration;
export type EasingToken = keyof typeof transitions.easing;