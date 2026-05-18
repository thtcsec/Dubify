export interface Voice {
  id: string;
  name: string;
  lang: string;
  gender: string;
  category?: string;
  accent?: string;
  style?: string;
}

/** Normalize /api/v1/voices — supports legacy array or { voices, groups }. */
export function parseVoicesResponse(data: unknown): Voice[] {
  if (Array.isArray(data)) {
    return data.filter(isVoice);
  }
  if (data && typeof data === 'object' && 'voices' in data) {
    const voices = (data as { voices?: unknown }).voices;
    if (Array.isArray(voices)) {
      return voices.filter(isVoice);
    }
  }
  return [];
}

function isVoice(value: unknown): value is Voice {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const v = value as Record<string, unknown>;
  return typeof v.id === 'string' && typeof v.name === 'string' && typeof v.lang === 'string';
}

export function asVoiceList(voices: unknown): Voice[] {
  return Array.isArray(voices) ? voices.filter(isVoice) : parseVoicesResponse(voices);
}
