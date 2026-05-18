const SECTION_RE = /^\s*\[([^\]]+)\]\s*$/gm;

export interface StudioScenePreview {
  title: string;
  body: string;
}

export function parseStudioScenes(text: string): StudioScenePreview[] {
  const cleaned = text.trim();
  if (!cleaned) return [];

  const scenes: StudioScenePreview[] = [];
  const matches = [...cleaned.matchAll(SECTION_RE)];

  if (matches.length === 0) {
    return [{ title: '', body: cleaned }];
  }

  if (matches[0].index! > 0) {
    const intro = cleaned.slice(0, matches[0].index).trim();
    if (intro) scenes.push({ title: '', body: intro });
  }

  matches.forEach((match, i) => {
    const title = match[1].trim();
    const start = match.index! + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index! : cleaned.length;
    const body = cleaned.slice(start, end).trim();
    scenes.push({ title, body });
  });

  return scenes;
}
