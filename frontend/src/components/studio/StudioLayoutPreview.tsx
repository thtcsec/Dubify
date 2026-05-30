import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { GripHorizontal, Move, RotateCcw } from 'lucide-react';
import { parseStudioScenes } from '@/lib/studioScenes';
import { parseScriptPopups, spokenTextWithoutPopups } from '@/lib/scriptPopups';
import {
  BAND_HEIGHT_PCT,
  clampLayout,
  defaultStudioLayout,
  type StudioLayoutPositions,
} from '@/lib/studioLayout';
import { useI18n } from '@/i18n/I18nProvider';
import { aspectPreviewFrameStyle } from '@/lib/aspectRatios';
import { scenePreviewImageUrl } from '@/lib/scenePreviewImage';
import { Button } from '../ui/button';

function isGenericSceneTitle(title: string): boolean {
  return /^(hook|story|insight|close|mở đầu|kết|cảnh\s*\d+|scene\s*\d+)$/i.test(title.trim());
}

export interface StudioLayoutPreviewProps {
  script: string;
  imagePreview: string;
  /** Timeline length for scrubber (defaults to scene count × 3.2s) */
  previewDurationSeconds?: number;
  aspectRatio: string;
  template: 'tiktok_news' | 'tiktok_news_pill';
  layout: StudioLayoutPositions;
  onLayoutChange: (layout: StudioLayoutPositions) => void;
  headerEnabled: boolean;
  headerText: string;
  headerOpacity: number;
  footerEnabled: boolean;
  footerText: string;
  footerOpacity: number;
  socialOverlay: 'none' | 'tiktok_follow' | 'yt_lower_third';
  socialHandle: string;
  socialSubtitle: string;
  socialAvatarUrl?: string;
  /** Topic label (preview uses gradient except wiki thumb on scene 0) */
  previewTopic?: string;
  wikiThumbnailUrl?: string;
}

type DragTarget = 'header' | 'footer' | 'social' | 'caption' | null;

function formatPreviewTime(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `0:${String(s).padStart(2, '0')}`;
}

export function StudioLayoutPreview({
  script,
  imagePreview,
  previewDurationSeconds,
  aspectRatio,
  template,
  layout,
  onLayoutChange,
  headerEnabled,
  headerText,
  headerOpacity,
  footerEnabled,
  footerText,
  footerOpacity,
  socialOverlay,
  socialHandle,
  socialSubtitle,
  socialAvatarUrl,
  previewTopic = '',
  wikiThumbnailUrl = '',
}: StudioLayoutPreviewProps) {
  const { t } = useI18n();
  const frameRef = useRef<HTMLDivElement>(null);
  const seekBarRef = useRef<HTMLDivElement>(null);
  const scenes = useMemo(() => parseStudioScenes(script), [script]);
  const [sceneIndex, setSceneIndex] = useState(0);
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [isSeeking, setIsSeeking] = useState(false);
  const wasPlayingBeforeSeek = useRef(false);
  const [dragTarget, setDragTarget] = useState<DragTarget>(null);
  const [showInfoCard, setShowInfoCard] = useState(false);

  const sceneWordCounts = useMemo(
    () =>
      scenes.map((s) => {
        const n = spokenTextWithoutPopups(`${s.title}\n${s.body}`).split(/\s+/).filter(Boolean).length;
        return Math.max(n, 8);
      }),
    [scenes],
  );
  const totalWords = sceneWordCounts.reduce((a, b) => a + b, 0) || 1;
  const sceneBasedDuration = Math.max(scenes.length, 1) * 3.2;
  const totalDuration = Math.max(
    previewDurationSeconds && previewDurationSeconds > 0 ? previewDurationSeconds : 0,
    sceneBasedDuration,
    12,
  );
  const sceneDurations = useMemo(
    () => sceneWordCounts.map((w) => (w / totalWords) * totalDuration),
    [sceneWordCounts, totalWords, totalDuration],
  );
  const sceneStarts = useMemo(() => {
    let cursor = 0;
    return sceneDurations.map((dur) => {
      const start = cursor;
      cursor += dur;
      return start;
    });
  }, [sceneDurations]);

  const scene = scenes[sceneIndex] ?? { title: '', body: '' };
  const sceneBgUrl = useMemo(() => {
    if (imagePreview) return imagePreview;
    if (!previewTopic.trim()) return '';
    return scenePreviewImageUrl(previewTopic, scene.title, sceneIndex, wikiThumbnailUrl);
  }, [imagePreview, previewTopic, scene.title, sceneIndex, wikiThumbnailUrl]);
  const frameStyle = aspectPreviewFrameStyle(aspectRatio);
  const pillTemplate = template === 'tiktok_news_pill';

  const resolveSceneAtTime = useCallback(
    (t: number) => {
      for (let i = sceneStarts.length - 1; i >= 0; i -= 1) {
        if (t >= sceneStarts[i] - 0.001) return i;
      }
      return 0;
    },
    [sceneStarts],
  );

  useEffect(() => {
    setPlayhead((p) => Math.min(p, Math.max(totalDuration - 0.05, 0)));
  }, [totalDuration]);

  useEffect(() => {
    if (!playing || isSeeking) return;
    const timer = window.setInterval(() => {
      setPlayhead((p) => {
        const next = p + 0.16;
        if (next >= totalDuration) {
          setPlaying(false);
          setSceneIndex(Math.max(scenes.length - 1, 0));
          return Math.max(totalDuration - 0.05, 0);
        }
        setSceneIndex(resolveSceneAtTime(next));
        return next;
      });
    }, 160);
    return () => window.clearInterval(timer);
  }, [playing, isSeeking, scenes.length, totalDuration, resolveSceneAtTime]);

  useEffect(() => {
    if (socialOverlay === 'none') {
      setShowInfoCard(false);
      return;
    }
    const tmr = window.setTimeout(() => setShowInfoCard(true), 600);
    return () => window.clearTimeout(tmr);
  }, [socialOverlay, sceneIndex]);

  const seekPlayhead = useCallback(
    (value: number) => {
      const t = Math.max(0, Math.min(value, totalDuration));
      setPlayhead(t);
      setSceneIndex(resolveSceneAtTime(t));
    },
    [totalDuration, resolveSceneAtTime],
  );

  const updateSeekFromClientX = useCallback(
    (clientX: number) => {
      const bar = seekBarRef.current;
      if (!bar || totalDuration <= 0) return;
      const rect = bar.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      seekPlayhead(ratio * totalDuration);
    },
    [seekPlayhead, totalDuration],
  );

  useEffect(() => {
    if (!isSeeking) return;
    const onMove = (e: PointerEvent) => updateSeekFromClientX(e.clientX);
    const onUp = () => {
      setIsSeeking(false);
      if (wasPlayingBeforeSeek.current) {
        setPlaying(true);
      }
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [isSeeking, updateSeekFromClientX]);

  const startDrag = useCallback(
    (target: DragTarget, e: React.PointerEvent) => {
      e.preventDefault();
      e.stopPropagation();
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      setDragTarget(target);
      setPlaying(false);
    },
    [],
  );

  const onDragMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragTarget || !frameRef.current) return;
      const rect = frameRef.current.getBoundingClientRect();
      const xPct = ((e.clientX - rect.left) / rect.width) * 100;
      const yPct = ((e.clientY - rect.top) / rect.height) * 100;
      const bottomPct = ((rect.bottom - e.clientY) / rect.height) * 100;

      onLayoutChange(
        clampLayout({
          ...layout,
          ...(dragTarget === 'header' ? { headerYPct: yPct - BAND_HEIGHT_PCT / 2 } : {}),
          ...(dragTarget === 'footer' ? { footerYPct: yPct - BAND_HEIGHT_PCT / 2 } : {}),
          ...(dragTarget === 'social'
            ? { socialLeftPct: xPct - 8, socialBottomPct: bottomPct - 4 }
            : {}),
          ...(dragTarget === 'caption' ? { captionYPct: yPct } : {}),
        }),
      );
    },
    [dragTarget, layout, onLayoutChange],
  );

  const endDrag = useCallback(() => {
    setDragTarget(null);
  }, []);

  const resetLayout = () => onLayoutChange(defaultStudioLayout(aspectRatio));

  const scenePopups = useMemo(
    () => parseScriptPopups(`${scene.title}\n${scene.body}`),
    [scene.title, scene.body],
  );

  const allSpokenWords = useMemo(
    () => spokenTextWithoutPopups(script).split(/\s+/).filter(Boolean),
    [script],
  );

  const sceneWords = useMemo(() => {
    const spoken = spokenTextWithoutPopups(scene.body || scene.title || '');
    return spoken.split(/\s+/).filter(Boolean);
  }, [scene.body, scene.title]);

  const sampleWords = useMemo(() => {
    if (sceneWords.length > 0) return sceneWords.slice(0, pillTemplate ? 6 : 10);
    return ['Xem', 'trước', 'phụ', 'đề', 'karaoke'];
  }, [sceneWords, pillTemplate]);

  const visiblePopup =
    scenePopups.length > 0
      ? scenePopups[Math.min(sceneIndex, scenePopups.length - 1)]
      : null;

  const globalWordIndex = Math.min(
    allSpokenWords.length - 1,
    Math.max(0, Math.floor((playhead / totalDuration) * allSpokenWords.length)),
  );
  const sceneStartWord = useMemo(() => {
    let offset = 0;
    for (let i = 0; i < sceneIndex; i += 1) {
      offset += sceneWordCounts[i] ?? 0;
    }
    return offset;
  }, [sceneIndex, sceneWordCounts]);
  const activeWord = Math.max(
    0,
    Math.min(sampleWords.length - 1, globalWordIndex - sceneStartWord),
  );

  if (scenes.length === 0) {
    return <p className="text-xs text-slate-500 text-center py-8">{t.studio.previewNeedScript}</p>;
  }

  return (
    <motion.div layout className="space-y-3">
      <motion.div layout className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300/90">
            {t.studio.layoutPreviewTitle}
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">{t.studio.layoutPreviewHint}</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-[10px] text-slate-400 gap-1"
          onClick={resetLayout}
        >
          <RotateCcw className="h-3 w-3" />
          {t.studio.layoutReset}
        </Button>
      </motion.div>

      <div
        ref={frameRef}
        className="relative overflow-hidden rounded-xl border border-cyan-500/25 bg-[#0a0e1a] shadow-lg select-none touch-none"
        style={frameStyle}
        onPointerMove={onDragMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
      >
        <motion.div
          className="absolute inset-0 bg-cover bg-center"
          style={
            sceneBgUrl
              ? { backgroundImage: `url(${sceneBgUrl})` }
              : { background: 'linear-gradient(160deg, #0b1020 0%, #1e3a5f 45%, #312e81 100%)' }
          }
          animate={{ scale: playing ? [1, 1.06] : 1 }}
          transition={{ duration: sceneDurations[sceneIndex] ?? 3.2, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute inset-0 bg-gradient-to-t from-[#0a0e1a]/90 via-[#0a0e1a]/35 to-[#0a0e1a]/20"
          initial={false}
        />

        {headerEnabled && (
          <div
            role="button"
            tabIndex={0}
            className={`absolute left-0 right-0 cursor-ns-resize border border-dashed rounded-sm transition-colors ${
              dragTarget === 'header' ? 'border-cyan-400 ring-2 ring-cyan-400/30' : 'border-white/25 hover:border-cyan-400/50'
            }`}
            style={{
              top: `${layout.headerYPct}%`,
              height: `${BAND_HEIGHT_PCT}%`,
              background: `rgba(8,12,24,${(headerOpacity / 100) * 0.65})`,
            }}
            onPointerDown={(e) => startDrag('header', e)}
          >
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[9px] uppercase tracking-wider text-cyan-200/80 flex items-center gap-1">
                <GripHorizontal className="h-3 w-3" />
                {t.studio.headerLabel}
              </span>
              <Move className="h-3 w-3 text-white/40" />
            </div>
            {headerText && (
              <p className="px-3 text-[11px] font-semibold text-white truncate">{headerText}</p>
            )}
          </div>
        )}

        {footerEnabled && (
          <div
            role="button"
            tabIndex={0}
            className={`absolute left-0 right-0 cursor-ns-resize border border-dashed rounded-sm transition-colors ${
              dragTarget === 'footer' ? 'border-cyan-400 ring-2 ring-cyan-400/30' : 'border-white/25 hover:border-cyan-400/50'
            }`}
            style={{
              top: `${layout.footerYPct}%`,
              height: `${BAND_HEIGHT_PCT}%`,
              background: `rgba(8,12,24,${(footerOpacity / 100) * 0.65})`,
            }}
            onPointerDown={(e) => startDrag('footer', e)}
          >
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[9px] uppercase tracking-wider text-cyan-200/80 flex items-center gap-1">
                <GripHorizontal className="h-3 w-3" />
                {t.studio.footerLabel}
              </span>
              <Move className="h-3 w-3 text-white/40" />
            </div>
            {footerText && (
              <p className="px-3 text-[11px] font-semibold text-white truncate">{footerText}</p>
            )}
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={`scene-${sceneIndex}-${scene.title}`}
            className="absolute inset-x-0 px-4 pointer-events-none"
            style={{ top: `${layout.captionYPct - (pillTemplate ? 6 : 10)}%` }}
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
          >
            {scene.title && !pillTemplate && !isGenericSceneTitle(scene.title) && (
              <span className="inline-block mb-2 rounded-full border border-cyan-400/40 bg-cyan-500/15 px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-cyan-100">
                {scene.title}
              </span>
            )}
            {pillTemplate ? (
              <motion.div
                className="mx-auto max-w-[92%] rounded-2xl border border-white/15 bg-black/55 px-4 py-2.5 backdrop-blur-md shadow-lg"
                layout
              >
                <p className="text-center text-sm font-bold leading-snug">
                  {sampleWords.map((w, i) => (
                    <span
                      key={`${w}-${i}`}
                      className={
                        i === activeWord
                          ? 'text-yellow-300 drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]'
                          : i < activeWord
                            ? 'text-white'
                            : 'text-slate-400'
                      }
                    >
                      {w}{' '}
                    </span>
                  ))}
                </p>
              </motion.div>
            ) : (
              <div className="rounded-xl border border-white/10 bg-black/45 px-4 py-3 backdrop-blur-sm">
                <p className="text-sm font-semibold text-white leading-snug line-clamp-3">
                  {scene.body.slice(0, 180)}
                </p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        <motion.div
          role="separator"
          aria-label={t.studio.captionDragLabel}
          className={`absolute left-2 right-2 h-0.5 cursor-ns-resize z-10 ${
            dragTarget === 'caption' ? 'bg-yellow-400' : 'bg-cyan-400/50'
          }`}
          style={{ top: `${layout.captionYPct}%` }}
          onPointerDown={(e) => startDrag('caption', e)}
        />

        <AnimatePresence>
          {visiblePopup && (
            <motion.div
              key={`${visiblePopup.type}-${visiblePopup.text}`}
              className="absolute left-1/2 -translate-x-1/2 z-30 max-w-[85%]"
              style={{ top: `${Math.max(18, layout.captionYPct - 22)}%` }}
              initial={{ opacity: 0, y: 20, scale: 0.85 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 420, damping: 24 }}
            >
              <motion.div
                className={`rounded-2xl border px-4 py-2.5 shadow-2xl backdrop-blur-md text-center ${
                  visiblePopup.type === 'stat'
                    ? 'border-yellow-400/50 bg-yellow-500/20 text-yellow-100'
                    : 'border-violet-400/50 bg-violet-500/20 text-violet-100'
                }`}
                animate={{ scale: [1, 1.04, 1] }}
                transition={{ repeat: Infinity, duration: 1.8 }}
              >
                <span className="text-[9px] font-bold uppercase tracking-widest block opacity-80">
                  {visiblePopup.type === 'stat' ? t.studio.popupStat : t.studio.popupDef}
                </span>
                <span className="text-sm font-bold">{visiblePopup.text}</span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {socialOverlay !== 'none' && (
          <motion.div
            className={`absolute z-20 cursor-grab active:cursor-grabbing ${
              dragTarget === 'social' ? 'ring-2 ring-pink-400/60' : ''
            }`}
            style={{ left: `${layout.socialLeftPct}%`, bottom: `${layout.socialBottomPct}%` }}
            initial={{ opacity: 0, x: -24, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 22, delay: 0.15 }}
            onPointerDown={(e) => startDrag('social', e)}
          >
            {socialOverlay === 'tiktok_follow' ? (
              <motion.div
                className="flex items-center gap-2 rounded-full border border-white/20 bg-black/70 pl-1 pr-3 py-1 shadow-xl backdrop-blur-md"
                animate={showInfoCard ? { scale: [1, 1.03, 1] } : {}}
                transition={{ repeat: Infinity, duration: 2.2 }}
              >
                {socialAvatarUrl ? (
                  <img src={socialAvatarUrl} alt="" className="h-8 w-8 rounded-full object-cover" />
                ) : (
                  <motion.div
                    className="h-8 w-8 rounded-full bg-gradient-to-br from-pink-500 to-cyan-500"
                    animate={{ rotate: [0, 8, -8, 0] }}
                    transition={{ repeat: Infinity, duration: 4 }}
                  />
                )}
                <motion.div
                  initial={{ width: 0, opacity: 0 }}
                  animate={showInfoCard ? { width: 'auto', opacity: 1 } : { width: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <span className="text-xs font-bold text-white whitespace-nowrap pr-1">
                    {socialHandle || '@channel'}
                  </span>
                </motion.div>
                <span className="rounded-full bg-[#fe2c55] px-2.5 py-0.5 text-[10px] font-bold text-white">
                  Follow
                </span>
              </motion.div>
            ) : (
              <motion.div
                className="flex items-center gap-2 rounded-lg border border-white/15 bg-black/75 px-2 py-1.5 shadow-xl backdrop-blur-md min-w-[160px]"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {socialAvatarUrl ? (
                  <img src={socialAvatarUrl} alt="" className="h-9 w-9 rounded-md object-cover" />
                ) : (
                  <motion.div
                    className="h-9 w-9 rounded-md bg-red-600"
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ repeat: Infinity, duration: 2.5 }}
                  />
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-bold text-white truncate">{socialHandle || 'Channel'}</p>
                  <p className="text-[9px] text-slate-300 truncate">{socialSubtitle || 'Subscribe'}</p>
                </div>
                <span className="rounded bg-red-600 px-2 py-0.5 text-[9px] font-bold text-white">Subscribe</span>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      <motion.div layout className="space-y-2 rounded-lg border border-white/10 bg-black/30 p-2.5">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="h-7 w-7 shrink-0 rounded-md bg-white/10 text-white text-xs hover:bg-white/20"
            onClick={() => setPlaying((p) => !p)}
          >
            {playing ? '❚❚' : '▶'}
          </button>
          <span className="text-[10px] font-mono text-slate-400 tabular-nums w-14">
            {formatPreviewTime(playhead)}
          </span>
          <motion.div
            ref={seekBarRef}
            role="slider"
            aria-valuemin={0}
            aria-valuemax={totalDuration}
            aria-valuenow={playhead}
            className="relative flex-1 h-6 flex items-center cursor-pointer touch-none"
            onPointerDown={(e) => {
              e.preventDefault();
              e.stopPropagation();
              wasPlayingBeforeSeek.current = playing;
              setIsSeeking(true);
              setPlaying(false);
              updateSeekFromClientX(e.clientX);
            }}
          >
            <motion.div className="absolute inset-x-0 h-1.5 rounded-full bg-white/15" />
            <motion.div
              className="absolute left-0 h-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-indigo-500 pointer-events-none"
              style={{ width: `${totalDuration > 0 ? (playhead / totalDuration) * 100 : 0}%` }}
            />
            <motion.div
              className="absolute h-4 w-4 -ml-2 rounded-full bg-white shadow-lg border-2 border-cyan-400 pointer-events-none"
              style={{ left: `${totalDuration > 0 ? (playhead / totalDuration) * 100 : 0}%` }}
            />
          </motion.div>
          <span className="text-[10px] font-mono text-slate-500 tabular-nums w-14 text-right">
            {formatPreviewTime(totalDuration)}
          </span>
        </div>
        <motion.div className="flex flex-wrap gap-1">
          {scenes.map((s, i) => (
            <button
              key={`${s.title}-${i}`}
              type="button"
              onClick={() => {
                setSceneIndex(i);
                seekPlayhead(sceneStarts[i] ?? 0);
              }}
              className={`rounded-md px-2 py-0.5 text-[10px] border transition-colors ${
                i === sceneIndex
                  ? 'border-cyan-400/50 bg-cyan-500/15 text-cyan-100'
                  : 'border-white/10 text-slate-500 hover:border-white/20'
              }`}
            >
              {s.title || `#${i + 1}`}
            </button>
          ))}
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
