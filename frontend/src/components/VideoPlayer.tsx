import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize2 } from 'lucide-react';
import { Button } from './ui/button';

function formatTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

interface VideoPlayerProps {
  src: string;
  className?: string;
  maxHeightClass?: string;
}

export function VideoPlayer({ src, className = '', maxHeightClass = 'max-h-[min(70vh,560px)]' }: VideoPlayerProps) {
  const shellRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const seekBarRef = useRef<HTMLDivElement>(null);
  const seekingRef = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [seeking, setSeeking] = useState(false);

  const syncFromVideo = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    setCurrent(v.currentTime);
    if (Number.isFinite(v.duration) && v.duration > 0) {
      setDuration(v.duration);
    }
    setPlaying(!v.paused && !v.ended);
  }, []);

  useEffect(() => {
    seekingRef.current = seeking;
  }, [seeking]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.load();
    setCurrent(0);
    setDuration(0);
    setPlaying(false);
  }, [src]);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      if (!seekingRef.current) syncFromVideo();
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [syncFromVideo]);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
    syncFromVideo();
  };

  const seekTo = useCallback(
    (time: number) => {
      const v = videoRef.current;
      const d = duration > 0 ? duration : v && Number.isFinite(v.duration) ? v.duration : 0;
      if (d <= 0) return;
      const t = Math.max(0, Math.min(time, d));
      setCurrent(t);
      if (v) {
        try {
          v.currentTime = t;
        } catch {
          /* ignore seek while metadata loading */
        }
      }
    },
    [duration],
  );

  const seekFromClientX = useCallback(
    (clientX: number) => {
      const bar = seekBarRef.current;
      if (!bar) return;
      const rect = bar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      const d = duration > 0 ? duration : 1;
      seekTo(ratio * d);
    },
    [duration, seekTo],
  );

  const endSeek = useCallback(() => {
    const v = videoRef.current;
    if (v && duration > 0) {
      try {
        v.currentTime = current;
      } catch {
        /* ignore */
      }
    }
    seekingRef.current = false;
    setSeeking(false);
    syncFromVideo();
  }, [current, duration, syncFromVideo]);

  const startSeek = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    seekingRef.current = true;
    setSeeking(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    seekFromClientX(e.clientX);
  };

  const toggleFullscreen = async () => {
    const shell = shellRef.current;
    if (!shell) return;
    if (document.fullscreenElement) await document.exitFullscreen();
    else await shell.requestFullscreen();
  };

  const progressPct = duration > 0 ? (current / duration) * 100 : 0;

  return (
    <div
      ref={shellRef}
      className={`rounded-xl border border-white/10 bg-black overflow-hidden ${className}`}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <video
        ref={videoRef}
        src={src}
        playsInline
        preload="metadata"
        muted={muted}
        className={`block w-full ${maxHeightClass} bg-black cursor-pointer`}
        onClick={togglePlay}
        onLoadedMetadata={syncFromVideo}
        onDurationChange={syncFromVideo}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-950/95 border-t border-white/10">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 text-slate-200 hover:text-white"
          onClick={togglePlay}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
        </Button>
        <span className="text-[11px] font-mono text-slate-400 w-[72px] shrink-0 tabular-nums">
          {formatTime(current)} / {formatTime(duration)}
        </span>
        <div
          ref={seekBarRef}
          role="slider"
          aria-label="Seek"
          aria-valuemin={0}
          aria-valuemax={duration > 0 ? duration : 1}
          aria-valuenow={current}
          className="relative flex-1 h-5 flex items-center cursor-pointer touch-none min-w-0 group"
          onPointerDown={startSeek}
          onPointerMove={(e) => {
            if (!seekingRef.current) return;
            seekFromClientX(e.clientX);
          }}
          onPointerUp={endSeek}
          onPointerCancel={endSeek}
          onLostPointerCapture={endSeek}
        >
          <div className="absolute inset-x-0 h-1.5 rounded-full bg-white/15" />
          <div
            className="absolute left-0 h-1.5 rounded-full bg-indigo-500 pointer-events-none"
            style={{ width: `${progressPct}%` }}
          />
          <div
            className={`absolute h-3.5 w-3.5 -ml-[7px] rounded-full bg-white shadow border-2 border-indigo-400 pointer-events-none transition-transform ${
              seeking ? 'opacity-100 scale-110' : 'opacity-80 group-hover:opacity-100'
            }`}
            style={{ left: `${progressPct}%` }}
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 text-slate-400"
          onClick={() => setMuted((m) => !m)}
        >
          {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 text-slate-400"
          onClick={() => void toggleFullscreen()}
        >
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
