/**
 * responsive.ts — Shared responsive design constants and utilities.
 *
 * Central place for all breakpoint definitions, common responsive class
 * patterns, and helpers used across the app.
 *
 * ┌────────────┬───────────┬──────────────────────────────────────┐
 * │ Breakpoint │ Min-width │ Usage                                │
 * ├────────────┼───────────┼──────────────────────────────────────┤
 * │ sm         │ 640px     │ Small phones → large phones          │
 * │ md         │ 768px     │ Tablets (portrait)                   │
 * │ lg         │ 1024px    │ Tablets (landscape) / small laptops  │
 * │ xl         │ 1280px    │ Laptops / desktops                   │
 * │ 2xl        │ 1536px    │ Large desktops / ultrawides          │
 * └────────────┴───────────┴──────────────────────────────────────┘
 *
 * Key conventions:
 *  - Sidebar visibility breakpoint: lg (1024px)
 *  - Content padding: p-3 → sm:p-4 → md:p-6
 *  - Page headers: flex-col sm:flex-row
 *  - Grid cards: grid-cols-1 → sm:grid-cols-2 → lg:grid-cols-3 → xl:grid-cols-4
 */

/* ─── Breakpoint values (match Tailwind defaults) ─── */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

/* ─── Common responsive class patterns ─── */

/** Content area padding — use on page wrappers */
export const CONTENT_PADDING = 'p-3 sm:p-4 md:p-6';

/** Page header: title left, actions right. Stacks on mobile. */
export const PAGE_HEADER = 'flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6';

/** Page title text size */
export const PAGE_TITLE = 'text-xl sm:text-2xl font-bold text-slate-900 dark:text-white';

/** Standard card grid — 1 col on mobile, 2 on tablet, 3 on laptop, 4 on desktop */
export const CARD_GRID = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5';

/** Stat card grid — 2 col on mobile, 3 on laptop, 6 on xl */
export const STAT_GRID = 'grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4';

/** Detail info grid — 1 col mobile, 2 col tablet+ */
export const INFO_GRID_2 = 'grid grid-cols-1 sm:grid-cols-2 gap-4';

/** Detail info grid — 1 col mobile, 3 col tablet+ */
export const INFO_GRID_3 = 'grid grid-cols-1 sm:grid-cols-3 gap-4';

/** Row that wraps meta items nicely on mobile */
export const META_ROW = 'flex flex-wrap items-center gap-x-4 gap-y-1';

/** Button with responsive padding */
export const BTN_RESPONSIVE = 'px-3 sm:px-4 py-2 sm:py-2.5';

/** Hide on mobile, show on sm+ */
export const HIDE_MOBILE = 'hidden sm:block';

/** Show on mobile, hide on sm+ */
export const SHOW_MOBILE = 'sm:hidden';

/** Hide on mobile, show on lg+ (used for sidebar-related elements) */
export const HIDE_MOBILE_LG = 'hidden lg:block';

/** Show on mobile, hide on lg+ (used for hamburger etc.) */
export const SHOW_MOBILE_LG = 'lg:hidden';
