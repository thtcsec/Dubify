from pathlib import Path

path = Path(r"d:\tu_projects\Dubify\frontend\src\views\ActivityViews.tsx")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

start = None
end = None
for i, line in enumerate(lines):
    if "Processing Engine</Label>" in line:
        start = i - 2  # space-y-2 div
    if start is not None and end is None and i > start and "cloudStatusReady" in line:
        end = i - 1
        break

if start is None or end is None:
    raise SystemExit(f"markers not found start={start} end={end}")

replacement = """            <motion.div className="space-y-2">
              <Label className="text-[10px] uppercase text-slate-500">{t.settings.presetLabel}</Label>
              <Select
                value={processingPreset}
                onValueChange={(value: ProcessingPreset) => setProcessingPreset(value)}
                disabled={!isEditing}
              >
                <SelectTrigger className="bg-black/20 border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hybrid">{t.settings.presets.hybrid.label}</SelectItem>
                  <SelectItem value="local_offline">{t.settings.presets.local_offline.label}</SelectItem>
                  <SelectItem value="cloud_online">{t.settings.presets.cloud_online.label}</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[10px] text-slate-500">
                {processingPreset === 'local_offline'
                  ? t.settings.presets.local_offline.desc
                  : processingPreset === 'cloud_online'
                    ? t.settings.presets.cloud_online.desc
                    : t.settings.presets.hybrid.desc}
              </p>
              <p className="text-[10px] text-slate-600">{t.settings.presetHint}</p>
              {config?.capabilities && (
                <div className="grid grid-cols-3 gap-2 text-[10px] text-slate-500">
                  <div>{t.settings.capLlm}: {config.capabilities.cloud_llm ? t.common.on : t.common.off}</div>
                  <div>{t.settings.capTts}: {config.capabilities.network_tts ? t.common.on : t.common.off}</div>
                  <div>{t.settings.capUrl}: {config.capabilities.url_import ? t.common.on : t.common.off}</div>
                </div>
              )}
            </div>
"""

replacement = replacement.replace("<motion.div", "<div").replace("</motion.div>", "</div>")

# also fix title line above
for i, line in enumerate(lines):
    if "Default Models</CardTitle>" in line:
        lines[i] = line.replace("Default Models", "{t.settings.defaultModels}")

new_lines = lines[:start] + [replacement] + lines[end:]
path.write_text("".join(new_lines), encoding="utf-8")
print("patched", start, end)
