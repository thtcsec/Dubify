import { apiBaseUrl } from '@/lib/api';

export interface ResearchProgressEvent {
  phase: string;
  message: string;
  url?: string;
  issues?: string[];
  result?: ResearchStreamResult;
}

export interface ResearchStreamResult {
  topic: string;
  research_summary: string;
  confidence: string;
  sources: { title: string; url: string; snippet: string }[];
  script: string;
  wikipedia_used?: boolean;
  wiki_thumbnail_url?: string;
  target_duration_seconds?: number;
  suggested_duration_seconds?: number;
  word_count?: number;
  verification_issues?: string[];
}

function adminHeaders(): HeadersInit {
  const key = (import.meta.env.VITE_API_ADMIN_KEY || '').trim();
  return key ? { 'X-API-Key': key } : {};
}

export async function streamResearchTopic(
  topic: string,
  targetLang: string,
  onEvent: (event: ResearchProgressEvent) => void,
): Promise<ResearchStreamResult> {
  const form = new FormData();
  form.append('topic', topic);
  form.append('target_lang', targetLang);

  const response = await fetch(`${apiBaseUrl}/research-video/research-stream`, {
    method: 'POST',
    body: form,
    headers: adminHeaders(),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Research failed (${response.status})`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let finalResult: ResearchStreamResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as ResearchProgressEvent;
      if (event.phase === 'error') {
        throw new Error(event.message);
      }
      onEvent(event);
      if (event.phase === 'done' && event.result) {
        finalResult = event.result;
      }
    }
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer) as ResearchProgressEvent;
    if (event.phase === 'error') throw new Error(event.message);
    onEvent(event);
    if (event.phase === 'done' && event.result) finalResult = event.result;
  }

  if (!finalResult) {
    throw new Error('Research finished without a result');
  }
  return finalResult;
}
