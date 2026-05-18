export type ProcessingPreset = 'hybrid' | 'local_offline' | 'cloud_online';

export function presetToEngineMode(preset: ProcessingPreset): {
  processing_engine: 'local' | 'cloud';
  processing_mode: 'offline' | 'hybrid' | 'online';
} {
  switch (preset) {
    case 'local_offline':
      return { processing_engine: 'local', processing_mode: 'offline' };
    case 'cloud_online':
      return { processing_engine: 'cloud', processing_mode: 'online' };
    default:
      return { processing_engine: 'local', processing_mode: 'hybrid' };
  }
}

export function engineModeToPreset(engine?: string, mode?: string): ProcessingPreset {
  const e = (engine || 'local').toLowerCase();
  const m = (mode || 'hybrid').toLowerCase();
  if (e === 'cloud' && m === 'online') return 'cloud_online';
  if (e === 'local' && m === 'offline') return 'local_offline';
  return 'hybrid';
}
