import { Eye, LayoutTemplate } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { StudioLayoutPreview } from '@/components/studio/StudioLayoutPreview';
import { useI18n } from '@/i18n/I18nProvider';
import type { AspectRatioValue } from '@/lib/aspectRatios';
import type { StudioLayoutPositions } from '@/lib/studioLayout';
import type { SocialOverlayPreset } from '@/lib/studioBrandStore';

export interface SceneReviewCard {
  id: string;
  title: string;
  text: string;
  prompt: string;
  durationSeconds: number;
  approved: boolean;
  forceFallback: boolean;
  status: 'draft' | 'kept' | 'regenerated' | 'fallback';
}

interface StudioProjectPreviewProps {
  script: string;
  previewDurationSeconds?: number;
  previewTopic?: string;
  wikiThumbnailUrl?: string;
  aspectRatio: AspectRatioValue;
  template: 'tiktok_news' | 'tiktok_news_pill';
  layout: StudioLayoutPositions;
  onLayoutChange: (layout: StudioLayoutPositions) => void;
  headerEnabled: boolean;
  headerText: string;
  headerOpacity: number;
  footerEnabled: boolean;
  footerText: string;
  footerOpacity: number;
  socialOverlay: SocialOverlayPreset;
  socialHandle: string;
  socialSubtitle: string;
  socialAvatarUrl?: string;
  onOpenBrandLayout?: () => void;
  sticky?: boolean;
  sceneReviewCards?: SceneReviewCard[];
  onScenePromptChange?: (sceneId: string, prompt: string) => void;
  onRegenerateScene?: (sceneId: string) => void;
  onKeepScene?: (sceneId: string) => void;
  onFallbackScene?: (sceneId: string) => void;
}

export function StudioProjectPreview({
  script,
  previewDurationSeconds,
  previewTopic,
  wikiThumbnailUrl,
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
  onOpenBrandLayout,
  sticky = true,
  sceneReviewCards = [],
  onScenePromptChange,
  onRegenerateScene,
  onKeepScene,
  onFallbackScene,
}: StudioProjectPreviewProps) {
  const { t } = useI18n();

  return (
    <div
      className={`relative rounded-2xl border border-white/10 bg-slate-900/80 backdrop-blur-xl p-4 shadow-2xl space-y-3 ${
        sticky ? 'lg:sticky lg:top-4' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <Label className="text-base font-bold flex items-center gap-2">
          <span className="bg-cyan-500/20 text-cyan-400 p-1.5 rounded-lg">
            <Eye className="w-4 h-4" />
          </span>
          {t.studio.projectPreviewTitle}
        </Label>
        {onOpenBrandLayout && (
          <Button type="button" variant="ghost" size="sm" className="text-cyan-300 h-8" onClick={onOpenBrandLayout}>
            <LayoutTemplate className="w-3.5 h-3.5 mr-1" />
            {t.studio.openBrandLayout}
          </Button>
        )}
      </div>
      <p className="text-[11px] text-slate-500 leading-snug">{t.studio.projectPreviewHint}</p>
      <div className={sticky ? 'max-h-[min(70vh,640px)] overflow-y-auto pr-1' : ''}>
        {script.trim() ? (
          <div className="space-y-4">
            <StudioLayoutPreview
              script={script}
              imagePreview=""
              previewDurationSeconds={previewDurationSeconds}
              previewTopic={previewTopic}
              wikiThumbnailUrl={wikiThumbnailUrl}
              aspectRatio={aspectRatio}
              template={template}
              layout={layout}
              onLayoutChange={onLayoutChange}
              headerEnabled={headerEnabled}
              headerText={headerText}
              headerOpacity={headerOpacity}
              footerEnabled={footerEnabled}
              footerText={footerText}
              footerOpacity={footerOpacity}
              socialOverlay={socialOverlay}
              socialHandle={socialHandle}
              socialSubtitle={socialSubtitle}
              socialAvatarUrl={socialAvatarUrl}
            />

            {sceneReviewCards.length > 0 && (
              <div className="rounded-xl border border-cyan-500/20 bg-black/20 p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-cyan-100">{t.researchVideo.sceneReviewTitle}</p>
                    <p className="text-[11px] text-slate-400">{t.researchVideo.sceneReviewHint}</p>
                  </div>
                  <Badge className="bg-cyan-500/15 text-cyan-200 border-cyan-500/30">
                    {sceneReviewCards.length} {t.researchVideo.sceneCards}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {sceneReviewCards.map((scene, index) => (
                    <div key={scene.id} className="rounded-xl border border-white/10 bg-slate-950/70 p-4 space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                            {t.researchVideo.sceneLabel} {index + 1}
                          </p>
                          <p className="text-sm font-semibold text-slate-100">{scene.title}</p>
                        </div>
                        <Badge
                          className={
                            scene.forceFallback
                              ? 'bg-amber-500/20 text-amber-200 border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-200 border-emerald-500/30'
                          }
                        >
                          {scene.forceFallback ? t.researchVideo.sceneFallbackBadge : t.researchVideo.sceneReadyBadge}
                        </Badge>
                      </div>
                      <p className="text-xs leading-relaxed text-slate-300">{scene.text}</p>
                      <div className="space-y-2">
                        <Label className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t.researchVideo.promptLabel}
                        </Label>
                        <Textarea
                          value={scene.prompt}
                          onChange={(event) => onScenePromptChange?.(scene.id, event.target.value)}
                          className="min-h-[110px] bg-black/40 border-white/10 text-xs leading-relaxed"
                        />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => onRegenerateScene?.(scene.id)}>
                          {t.researchVideo.regeneratePrompt}
                        </Button>
                        <Button type="button" size="sm" variant="outline" onClick={() => onKeepScene?.(scene.id)}>
                          {t.researchVideo.keepScene}
                        </Button>
                        <Button type="button" size="sm" variant="outline" onClick={() => onFallbackScene?.(scene.id)}>
                          {t.researchVideo.fallbackScene}
                        </Button>
                        <span className="self-center text-[11px] text-slate-500">
                          ~{scene.durationSeconds}
                          {t.common.seconds}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-slate-500 text-center py-16 border border-dashed border-white/10 rounded-xl">
            {t.studio.projectPreviewEmpty}
          </p>
        )}
      </div>
    </div>
  );
}
