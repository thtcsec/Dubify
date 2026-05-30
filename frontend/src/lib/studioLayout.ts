/** Percent-based layout — matches backend `StudioLayout` / export pipeline. */

export interface StudioLayoutPositions {
  /** Top edge of header band (% of frame height). */
  headerYPct: number;
  /** Top edge of footer band (% of frame height). */
  footerYPct: number;
  socialLeftPct: number;
  /** Distance from bottom of frame (%). */
  socialBottomPct: number;
  /** Vertical center of karaoke / caption pill (% from top). */
  captionYPct: number;
}

export const BAND_HEIGHT_PCT = 11;

export function isPortraitAspect(aspectRatio: string): boolean {
  const [w, h] = aspectRatio.split(':').map(Number);
  return Number.isFinite(w) && Number.isFinite(h) && h > w;
}

export function defaultStudioLayout(aspectRatio: string): StudioLayoutPositions {
  const portrait = isPortraitAspect(aspectRatio);
  return {
    headerYPct: 0,
    footerYPct: portrait ? 89 : 88,
    socialLeftPct: 4.4,
    socialBottomPct: portrait ? 6.25 : 5,
    captionYPct: portrait ? 64 : 78,
  };
}

export function clampLayout(layout: StudioLayoutPositions): StudioLayoutPositions {
  const maxHeader = Math.max(0, layout.footerYPct - BAND_HEIGHT_PCT - 2);
  return {
    headerYPct: Math.max(0, Math.min(layout.headerYPct, maxHeader)),
    footerYPct: Math.max(layout.headerYPct + BAND_HEIGHT_PCT + 2, Math.min(layout.footerYPct, 100 - BAND_HEIGHT_PCT)),
    socialLeftPct: Math.max(0, Math.min(layout.socialLeftPct, 72)),
    socialBottomPct: Math.max(2, Math.min(layout.socialBottomPct, 92)),
    captionYPct: Math.max(22, Math.min(layout.captionYPct, 88)),
  };
}

export function layoutToFormFields(layout: StudioLayoutPositions): Record<string, string> {
  return {
    header_y_pct: String(layout.headerYPct),
    footer_y_pct: String(layout.footerYPct),
    social_left_pct: String(layout.socialLeftPct),
    social_bottom_pct: String(layout.socialBottomPct),
    caption_y_pct: String(layout.captionYPct),
  };
}
