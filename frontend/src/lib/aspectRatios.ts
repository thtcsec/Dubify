import type { CSSProperties } from 'react';

/** Shared aspect ratios — matches backend `ALLOWED_ASPECT_RATIOS`. */

export const ALLOWED_ASPECT_RATIOS = ['16:9', '9:16', '4:3', '3:4', '1:1'] as const;

export type AspectRatioValue = (typeof ALLOWED_ASPECT_RATIOS)[number];

export const ASPECT_RATIO_OPTIONS: { value: AspectRatioValue; labelKey: AspectRatioValue }[] = [
  { value: '16:9', labelKey: '16:9' },
  { value: '4:3', labelKey: '4:3' },
  { value: '9:16', labelKey: '9:16' },
  { value: '3:4', labelKey: '3:4' },
  { value: '1:1', labelKey: '1:1' },
];

export function isAllowedAspectRatio(value: string): value is AspectRatioValue {
  return (ALLOWED_ASPECT_RATIOS as readonly string[]).includes(value);
}

export function normalizeAspectRatio(value: string | undefined, fallback: AspectRatioValue = '16:9'): AspectRatioValue {
  if (value && isAllowedAspectRatio(value)) return value;
  return fallback;
}

export function parseAspectParts(aspectRatio: string): { w: number; h: number } {
  const [w, h] = aspectRatio.split(':').map(Number);
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    return { w: 16, h: 9 };
  }
  return { w, h };
}

/** CSS styles for WYSIWYG preview frames (width-driven; no maxHeight that breaks ratio). */
export function aspectPreviewFrameStyle(aspectRatio: string): CSSProperties {
  const { w, h } = parseAspectParts(aspectRatio);
  const portrait = h > w;
  const square = w === h;
  const base: CSSProperties = {
    aspectRatio: `${w} / ${h}`,
    width: '100%',
    marginLeft: 'auto',
    marginRight: 'auto',
  };
  if (portrait) {
    return { ...base, maxWidth: 'min(100%, 300px)' };
  }
  if (square) {
    return { ...base, maxWidth: 'min(100%, 400px)' };
  }
  return { ...base, maxWidth: 'min(100%, 720px)' };
}
