import { useEffect, useMemo, useState } from 'react';
import { parseStudioScenes } from '@/lib/studioScenes';
import { useI18n } from '@/i18n/I18nProvider';

interface StudioScenePreviewProps {
  script: string;
  imagePreview: string;
  aspectRatio: string;
}

function StudioScenePreviewInner({ script, imagePreview, aspectRatio }: StudioScenePreviewProps) {
  const { t } = useI18n();
  const scenes = useMemo(() => parseStudioScenes(script), [script]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (scenes.length <= 1) return;
    const timer = window.setInterval(() => {
      setIndex((i) => (i + 1) % scenes.length);
    }, 3200);
    return () => window.clearInterval(timer);
  }, [scenes.length]);

  const scene = scenes[index] ?? { title: '', body: '' };
  const previewAspect = aspectRatio.replace(':', ' / ');

  if (scenes.length === 0) {
    return (
      <p className="text-xs text-slate-500 text-center py-8">{t.studio.previewNeedScript}</p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300/90">
          {t.studio.htmlPreview}
        </p>
        <span className="text-[10px] text-slate-500">
          {index + 1}/{scenes.length} · {t.studio.autoTransition}
        </span>
      </div>
      <div
        className="relative mx-auto w-full overflow-hidden rounded-xl border border-cyan-500/20 bg-[#0a0e1a] shadow-lg"
        style={{ aspectRatio: previewAspect, maxHeight: 420 }}
      >
        <div
          className="absolute inset-0 bg-cover bg-center transition-all duration-700"
          style={
            imagePreview
              ? { backgroundImage: `url(${imagePreview})`, filter: 'brightness(0.5) saturate(1.1)' }
              : {
                  background: 'linear-gradient(160deg, #0b1020 0%, #1e3a5f 45%, #312e81 100%)',
                }
          }
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0e1a]/95 via-[#0a0e1a]/50 to-transparent" />
        <div key={`${index}-${scene.title}`} className="absolute inset-x-0 bottom-0 p-5 space-y-3">
          {scene.title && (
            <span className="inline-block rounded-full border border-cyan-400/40 bg-cyan-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-cyan-200">
              {scene.title}
            </span>
          )}
          <p className="text-sm md:text-base font-semibold text-white leading-snug line-clamp-4">
            {scene.body.slice(0, 220)}
            {scene.body.length > 220 ? '…' : ''}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {scenes.map((s, i) => (
          <button
            key={`${s.title}-${i}`}
            type="button"
            onClick={() => setIndex(i)}
            className={`rounded-md px-2 py-1 text-[10px] border transition-colors ${
              i === index
                ? 'border-cyan-400/50 bg-cyan-500/15 text-cyan-100'
                : 'border-white/10 text-slate-500 hover:border-white/20'
            }`}
          >
            {s.title || `#${i + 1}`}
          </button>
        ))}
      </div>
    </div>
  );
}

export function StudioScenePreview(props: StudioScenePreviewProps) {
  return <StudioScenePreviewInner key={props.script} {...props} />;
}
