export interface SubtitleCue {
  id: number;
  start: string;
  end: string;
  text: string;
  startSec: number;
  endSec: number;
}

export function srtTimeToSeconds(value: string): number {
  const trimmed = value.trim();
  const [timePart, msPart] = trimmed.includes(',') ? trimmed.split(',') : trimmed.split('.');
  const segments = timePart.split(':').map(Number);
  if (segments.length < 3) return 0;
  const [h, m, s] = segments;
  const ms = msPart ? Number(msPart.padEnd(3, '0').slice(0, 3)) / 1000 : 0;
  return h * 3600 + m * 60 + s + ms;
}

export function secondsToSrtTime(seconds: number): string {
  const totalMs = Math.max(0, Math.round(seconds * 1000));
  const h = Math.floor(totalMs / 3_600_000);
  const m = Math.floor((totalMs % 3_600_000) / 60_000);
  const s = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

export function parseSrt(raw: string): SubtitleCue[] {
  const blocks = raw.split(/\r?\n\r?\n/).map((b) => b.trim()).filter(Boolean);
  const cues: SubtitleCue[] = [];

  for (const block of blocks) {
    const lines = block.split(/\r?\n/).filter(Boolean);
    const timeIdx = lines.findIndex((l) => l.includes('-->'));
    if (timeIdx === -1) continue;
    const [start, end] = lines[timeIdx].split('-->').map((x) => x.trim());
    const text = lines.slice(timeIdx + 1).join('\n').trim();
    if (!text) continue;
    const startSec = srtTimeToSeconds(start);
    const endSec = srtTimeToSeconds(end);
    cues.push({
      id: cues.length + 1,
      start,
      end,
      text,
      startSec,
      endSec,
    });
  }
  return cues;
}

export function cuesToSrt(cues: SubtitleCue[]): string {
  return cues
    .map((cue, i) => {
      const start = secondsToSrtTime(cue.startSec);
      const end = secondsToSrtTime(cue.endSec);
      return `${i + 1}\n${start} --> ${end}\n${cue.text.trim()}\n`;
    })
    .join('\n');
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  const ss = String(s % 60).padStart(2, '0');
  const mm = String(m % 60).padStart(2, '0');
  if (h > 0) return `${h}:${mm}:${ss}`;
  return `${mm}:${ss}`;
}
