import { motion } from 'framer-motion';
import { LayoutTemplate, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { StudioLayoutPreview } from '@/components/studio/StudioLayoutPreview';
import { useI18n } from '@/i18n/I18nProvider';
import { ASPECT_RATIO_OPTIONS, type AspectRatioValue } from '@/lib/aspectRatios';
import { useStudioBrand } from '@/lib/studioBrandStore';

export function BrandLayoutView() {
  const { t } = useI18n();
  const {
    brand,
    setBrand,
    setLayout,
    setPreviewAspect,
    setDefaultAspect,
    headerImagePreview,
    footerImagePreview,
    socialAvatarPreview,
    setHeaderImage,
    setFooterImage,
    setSocialAvatar,
  } = useStudioBrand();

  const previewScript =
    '[Hook]\n' +
    (brand.headerText ? `${brand.headerText}. ` : '') +
    'Tin nóng hôm nay.\n' +
    '[STAT: 47% — tăng trưởng YoY]\n' +
    '[DEF: Gemini — AI điều khiển thao tác trên điện thoại]\n' +
    'Theo dõi kênh để cập nhật thêm.';

  const aspectLabel = (value: AspectRatioValue) => {
    const key = value.replace(':', '_') as '16_9' | '9_16' | '4_3' | '3_4' | '1_1';
    return t.brandLayout.ratios[key] ?? value;
  };

  const renderBand = (
    enabled: boolean,
    setEnabled: (v: boolean) => void,
    text: string,
    setText: (v: string) => void,
    opacity: number,
    setOpacity: (v: number) => void,
    onFile: (f: File | null) => void,
    fileName: string | undefined,
    label: string,
  ) => (
    <motion.div className="rounded-xl border border-white/10 bg-black/30 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <Switch checked={enabled} onCheckedChange={setEnabled} />
      </div>
      {enabled && (
        <div className="space-y-3">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t.studio.brandingTextPlaceholder}
            className="bg-black/40 border-white/10 h-10 rounded-lg"
          />
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-500">{t.studio.brandingLogo}</Label>
            <Input
              type="file"
              accept="image/*"
              className="bg-black/40 border-white/10 text-xs file:mr-3 file:rounded-md file:border-0 file:bg-indigo-500/20 file:px-3 file:py-1.5"
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
            {fileName && <p className="text-[11px] text-slate-500 truncate">{fileName}</p>}
          </div>
          <div className="space-y-1.5">
            <motion.div className="flex justify-between text-xs text-slate-500">
              <span>{t.studio.brandingOpacity}</span>
              <span>{opacity}%</span>
            </motion.div>
            <input
              type="range"
              min={5}
              max={100}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
          </div>
        </div>
      )}
    </motion.div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">
          <span className="bg-gradient-to-br from-cyan-400 to-indigo-500 text-transparent bg-clip-text">
            {t.brandLayout.title}
          </span>
        </h1>
        <p className="text-slate-400">{t.brandLayout.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="space-y-4 rounded-2xl border border-white/10 bg-slate-900/60 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <LayoutTemplate className="w-4 h-4 text-cyan-400" />
            {t.brandLayout.previewFormat}
          </div>
          <div className="flex flex-wrap gap-2">
            {ASPECT_RATIO_OPTIONS.map((opt) => (
              <Button
                key={opt.value}
                type="button"
                size="sm"
                variant={brand.previewAspectRatio === opt.value ? 'default' : 'outline'}
                className={
                  brand.previewAspectRatio === opt.value
                    ? 'bg-cyan-600 hover:bg-cyan-500'
                    : 'border-white/10 bg-black/30'
                }
                onClick={() => setPreviewAspect(opt.value)}
              >
                {aspectLabel(opt.value)}
              </Button>
            ))}
          </div>

          <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 space-y-2">
            <p className="text-xs font-semibold text-cyan-200/90">{t.brandLayout.defaultFormat}</p>
            <p className="text-[10px] text-slate-500">{t.brandLayout.defaultFormatHint}</p>
            <div className="flex flex-wrap gap-2 items-center">
              <Select
                value={brand.defaultAspectRatio}
                onValueChange={(v) => setDefaultAspect(v as AspectRatioValue)}
              >
                <SelectTrigger className="w-[180px] bg-black/40 border-white/10 h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIO_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {aspectLabel(opt.value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="border-white/10 gap-1.5"
                onClick={() => setDefaultAspect(brand.previewAspectRatio)}
              >
                <Star className="h-3.5 w-3.5 text-amber-400" />
                {t.brandLayout.usePreviewAsDefault}
              </Button>
            </div>
          </div>

          <StudioLayoutPreview
            script={previewScript}
            imagePreview=""
            aspectRatio={brand.previewAspectRatio}
            template={brand.studioTemplate}
            layout={brand.layout}
            onLayoutChange={setLayout}
            headerEnabled={brand.headerEnabled}
            headerText={brand.headerText}
            headerOpacity={brand.headerOpacity}
            footerEnabled={brand.footerEnabled}
            footerText={brand.footerText}
            footerOpacity={brand.footerOpacity}
            socialOverlay={brand.socialOverlay}
            socialHandle={brand.socialHandle}
            socialSubtitle={brand.socialSubtitle}
            socialAvatarUrl={socialAvatarPreview || undefined}
          />
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-3">
            <Label className="text-xs uppercase tracking-wider text-slate-500">{t.studio.sceneTemplate}</Label>
            <Select
              value={brand.studioTemplate}
              onValueChange={(v) => setBrand({ studioTemplate: v as 'tiktok_news' | 'tiktok_news_pill' })}
            >
              <SelectTrigger className="bg-black/40 border-white/10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tiktok_news">{t.studio.templateNews}</SelectItem>
                <SelectItem value="tiktok_news_pill">{t.studio.templatePill}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-xl border border-white/10 bg-black/20 p-4 space-y-3">
            <Label className="text-xs uppercase tracking-wider text-slate-500">{t.studio.socialOverlay}</Label>
            <Select
              value={brand.socialOverlay}
              onValueChange={(v) =>
                setBrand({ socialOverlay: v as 'none' | 'tiktok_follow' | 'yt_lower_third' })
              }
            >
              <SelectTrigger className="bg-black/40 border-white/10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t.studio.socialNone}</SelectItem>
                <SelectItem value="tiktok_follow">{t.studio.socialTiktok}</SelectItem>
                <SelectItem value="yt_lower_third">{t.studio.socialYoutube}</SelectItem>
              </SelectContent>
            </Select>
            {brand.socialOverlay !== 'none' && (
              <>
                <Input
                  value={brand.socialHandle}
                  onChange={(e) => setBrand({ socialHandle: e.target.value })}
                  placeholder="@username"
                  className="bg-black/40 border-white/10 h-10"
                />
                {brand.socialOverlay === 'yt_lower_third' && (
                  <Input
                    value={brand.socialSubtitle}
                    onChange={(e) => setBrand({ socialSubtitle: e.target.value })}
                    placeholder={t.studio.socialSubtitlePlaceholder}
                    className="bg-black/40 border-white/10 h-10"
                  />
                )}
                <Input
                  type="file"
                  accept="image/*"
                  className="bg-black/40 border-white/10 text-xs"
                  onChange={(e) => setSocialAvatar(e.target.files?.[0] ?? null)}
                />
              </>
            )}
          </div>

          {renderBand(
            brand.headerEnabled,
            (v) => setBrand({ headerEnabled: v }),
            brand.headerText,
            (v) => setBrand({ headerText: v }),
            brand.headerOpacity,
            (v) => setBrand({ headerOpacity: v }),
            setHeaderImage,
            headerImagePreview ? 'logo' : undefined,
            t.studio.headerLabel,
          )}
          {renderBand(
            brand.footerEnabled,
            (v) => setBrand({ footerEnabled: v }),
            brand.footerText,
            (v) => setBrand({ footerText: v }),
            brand.footerOpacity,
            (v) => setBrand({ footerOpacity: v }),
            setFooterImage,
            footerImagePreview ? 'logo' : undefined,
            t.studio.footerLabel,
          )}

          <p className="text-[11px] text-slate-500 leading-snug">{t.brandLayout.sharedHint}</p>
        </div>
      </div>
    </div>
  );
}
