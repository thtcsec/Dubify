import { useCallback, useEffect, useRef, useState } from 'react';

interface EditorTimelineScrubberProps {
  duration: number;
  playhead: number;
  onSeek: (seconds: number) => void;
  onScrubStart?: () => void;
  onScrubEnd?: () => void;
  className?: string;
}

export function EditorTimelineScrubber({
  duration,
  playhead,
  onSeek,
  onScrubStart,
  onScrubEnd,
  className = '',
}: EditorTimelineScrubberProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const seekingRef = useRef(false);
  const [seeking, setSeeking] = useState(false);

  useEffect(() => {
    seekingRef.current = seeking;
  }, [seeking]);

  const seekFromX = useCallback(
    (clientX: number) => {
      const bar = barRef.current;
      const d = duration > 0 ? duration : 0;
      if (!bar || d <= 0) return;
      const rect = bar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      onSeek(ratio * d);
    },
    [duration, onSeek],
  );

  const endSeek = useCallback(() => {
    seekingRef.current = false;
    setSeeking(false);
    onScrubEnd?.();
  }, [onScrubEnd]);

  const startSeek = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    seekingRef.current = true;
    setSeeking(true);
    onScrubStart?.();
    e.currentTarget.setPointerCapture(e.pointerId);
    seekFromX(e.clientX);
  };

  const pct = duration > 0 ? (playhead / duration) * 100 : 0;

  return (
    <div
      ref={barRef}
      role="slider"
      aria-label="Timeline"
      aria-valuemin={0}
      aria-valuemax={duration}
      aria-valuenow={playhead}
      className={`relative h-6 flex items-center cursor-pointer touch-none select-none ${className}`}
      onPointerDown={startSeek}
      onPointerMove={(e) => {
        if (!seekingRef.current) return;
        seekFromX(e.clientX);
      }}
      onPointerUp={endSeek}
      onPointerCancel={endSeek}
      onLostPointerCapture={endSeek}
    >
      <div className="absolute inset-x-0 h-2 rounded-full bg-slate-800 border border-white/10" />
      <div
        className="absolute left-0 h-2 rounded-full bg-gradient-to-r from-red-500/80 to-orange-400/80 pointer-events-none"
        style={{ width: `${pct}%` }}
      />
      <div
        className={`absolute h-4 w-4 -ml-2 rounded-full bg-red-400 border-2 border-white shadow-lg pointer-events-none transition-transform ${
          seeking ? 'scale-125' : ''
        }`}
        style={{ left: `${pct}%` }}
      />
    </div>
  );
}
