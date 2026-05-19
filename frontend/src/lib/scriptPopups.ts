export interface ScriptPopup {
  type: 'stat' | 'def';
  text: string;
}

const POPUP_RE = /\[(STAT|DEF):\s*([^\]]+)\]/gi;

export function parseScriptPopups(text: string): ScriptPopup[] {
  const items: ScriptPopup[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(POPUP_RE.source, 'gi');
  while ((match = re.exec(text)) !== null) {
    const kind = match[1].toUpperCase();
    items.push({
      type: kind === 'STAT' ? 'stat' : 'def',
      text: match[2].trim(),
    });
  }
  return items;
}

export function spokenTextWithoutPopups(text: string): string {
  return text.replace(POPUP_RE, '').replace(/\s+/g, ' ').trim();
}
