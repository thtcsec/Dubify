import { Eye, LayoutTemplate } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { StudioLayoutPreview } from '@/components/studio/StudioLayoutPreview';
import { useI18n } from '@/i18n/I18nProvider';
import type { AspectRatioValue } from '@/lib/aspectRatios';
import type { StudioLayoutPositions } from '@/lib/studioLayout';
import type { SocialOverlayPreset } from '@/lib/studioBrandStore';

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
        ) : (
          <p className="text-xs text-slate-500 text-center py-16 border border-dashed border-white/10 rounded-xl">
            {t.studio.projectPreviewEmpty}
          </p>
        )}
      </div>
    </div>
  );
}
