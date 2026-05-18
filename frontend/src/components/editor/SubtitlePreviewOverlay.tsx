import { useEffect, useRef, useState } from 'react';
import type { SubtitleCue } from '@/lib/subtitles';
import {
  activeCueAt,
  DEFAULT_SUBTITLE_STYLE,
  subtitleFontPx,
  subtitleMarginPx,
  wrapSubtitleText,
  type SubtitleStyle,
} from '@/lib/subtitleStyle';

interface SubtitlePreviewOverlayProps {
  cues: SubtitleCue[];
  playhead: number;
  enabled?: boolean;
  style?: SubtitleStyle;
  emptyHint?: string;
}

export function SubtitlePreviewOverlay({
  cues,
  playhead,
  enabled = true,
  style = DEFAULT_SUBTITLE_STYLE,
  emptyHint = 'No subtitle at playhead',
}: SubtitlePreviewOverlayProps) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [boxHeight, setBoxHeight] = useState(360);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBoxHeight(el.clientHeight || 360));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const cue = activeCueAt(cues, playhead);
  const display = cue
    ? wrapSubtitleText(cue.text, style.maxCharsPerLine, style.maxLines)
    : '';

  const fontSize = subtitleFontPx(boxHeight, style.fontScale);
  const marginBottom = subtitleMarginPx(boxHeight, style.marginScale);

  return (
    <div
      ref={boxRef}
      className="pointer-events-none absolute inset-0 flex items-end justify-center"
      aria-hidden={!enabled || !display}
    >
      {enabled && display ? (
        <div
          className="max-w-[92%] text-center font-semibold leading-snug text-white"
          style={{
            fontSize,
            marginBottom,
            textShadow:
              '0 0 4px rgba(0,0,0,0.95), 0 2px 8px rgba(0,0,0,0.85), 1px 1px 0 #000',
            WebkitTextStroke: '1px rgba(0,0,0,0.35)',
          }}
        >
          {display.split('\n').map((line, i) => (
            <div key={`${cue?.id}-${i}`}>{line}</div>
          ))}
        </div>
      ) : enabled && !display ? (
        <div
          className="rounded-md border border-dashed border-white/20 bg-black/40 px-3 py-1.5 text-[10px] uppercase tracking-wider text-slate-400"
          style={{ marginBottom }}
        >
          {emptyHint}
        </div>
      ) : null}
    </div>
  );
}
