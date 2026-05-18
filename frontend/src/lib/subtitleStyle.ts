/** Matches backend VideoService._subtitle_style_for_height ratios. */

export interface SubtitleStyle {
  fontScale: number;
  marginScale: number;
  maxCharsPerLine: number;
  maxLines: number;
}

export const DEFAULT_SUBTITLE_STYLE: SubtitleStyle = {
  fontScale: 1,
  marginScale: 1,
  maxCharsPerLine: 42,
  maxLines: 2,
};

export function subtitleFontPx(containerHeight: number, fontScale = 1): number {
  const base = Math.max(18, Math.min(36, containerHeight * 0.038));
  return Math.round(base * fontScale);
}

export function subtitleMarginPx(containerHeight: number, marginScale = 1): number {
  const base = Math.max(32, containerHeight * 0.075);
  return Math.round(base * marginScale);
}

export function wrapSubtitleText(
  text: string,
  maxChars = DEFAULT_SUBTITLE_STYLE.maxCharsPerLine,
  maxLines = DEFAULT_SUBTITLE_STYLE.maxLines,
): string {
  const cleaned = text.replace(/\s+/g, ' ').trim();
  if (!cleaned || cleaned.length <= maxChars) return cleaned;

  const words = cleaned.split(' ');
  const lines: string[] = [];
  let current: string[] = [];
  let length = 0;

  for (const word of words) {
    const extra = word.length + (current.length ? 1 : 0);
    if (current.length && length + extra > maxChars) {
      lines.push(current.join(' '));
      current = [word];
      length = word.length;
      if (lines.length >= maxLines) break;
    } else {
      current.push(word);
      length += extra;
    }
  }
  if (current.length && lines.length < maxLines) {
    lines.push(current.join(' '));
  }
  if (lines.length > maxLines) lines.length = maxLines;
  return lines.join('\n');
}

export function activeCueAt<T extends { startSec: number; endSec: number }>(
  cues: T[],
  timeSec: number,
): T | null {
  return cues.find((c) => timeSec >= c.startSec && timeSec <= c.endSec) ?? null;
}
