/**
 * useBreakpoint — responsive breakpoint detection hook.
 *
 * Provides reactive breakpoint info matching Tailwind CSS defaults:
 *   sm: 640px  |  md: 768px  |  lg: 1024px  |  xl: 1280px  |  2xl: 1536px
 *
 * Usage:
 *   const { isMobile, isTablet, isDesktop, breakpoint } = useBreakpoint();
 *
 *   isMobile   → < 768px  (phones)
 *   isTablet   → 768px–1023px  (tablets in portrait/landscape)
 *   isDesktop  → ≥ 1024px (laptops, desktops)
 *   breakpoint → 'sm' | 'md' | 'lg' | 'xl' | '2xl'
 *
 * The hook uses matchMedia for efficient, debounce-free updates.
 */

import { useState, useEffect, useMemo } from 'react';

export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export type BreakpointKey = keyof typeof BREAKPOINTS;

export interface BreakpointInfo {
  /** Current named breakpoint */
  breakpoint: BreakpointKey;
  /** True when viewport < 768px (phone) */
  isMobile: boolean;
  /** True when viewport ≥ 768px and < 1024px (tablet) */
  isTablet: boolean;
  /** True when viewport ≥ 1024px */
  isDesktop: boolean;
  /** Current viewport width in px */
  width: number;
}

function getBreakpoint(w: number): BreakpointKey {
  if (w >= BREAKPOINTS['2xl']) return '2xl';
  if (w >= BREAKPOINTS.xl) return 'xl';
  if (w >= BREAKPOINTS.lg) return 'lg';
  if (w >= BREAKPOINTS.md) return 'md';
  return 'sm';
}

export function useBreakpoint(): BreakpointInfo {
  const [width, setWidth] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth : 1280
  );

  useEffect(() => {
    // Use matchMedia queries for efficient change detection
    const queries = Object.values(BREAKPOINTS).map((bp) => {
      const mql = window.matchMedia(`(min-width: ${bp}px)`);
      const handler = () => setWidth(window.innerWidth);
      mql.addEventListener('change', handler);
      return { mql, handler };
    });

    // Also listen to resize for edge cases
    const resizeHandler = () => setWidth(window.innerWidth);
    window.addEventListener('resize', resizeHandler);

    return () => {
      queries.forEach(({ mql, handler }) =>
        mql.removeEventListener('change', handler)
      );
      window.removeEventListener('resize', resizeHandler);
    };
  }, []);

  return useMemo(() => {
    const breakpoint = getBreakpoint(width);
    return {
      breakpoint,
      isMobile: width < BREAKPOINTS.md,
      isTablet: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
      isDesktop: width >= BREAKPOINTS.lg,
      width,
    };
  }, [width]);
}

/**
 * Utility: returns true if current viewport matches the given query.
 *
 * Usage:
 *   const isNarrow = useMediaQuery('(max-width: 640px)');
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia(query).matches
      : false
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    setMatches(mql.matches);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
