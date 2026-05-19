import { useCallback, useEffect, useSyncExternalStore } from 'react';
import {
  defaultStudioLayout,
  type StudioLayoutPositions,
} from '@/lib/studioLayout';
import {
  type AspectRatioValue,
  isAllowedAspectRatio,
  normalizeAspectRatio,
} from '@/lib/aspectRatios';

export type SocialOverlayPreset = 'none' | 'tiktok_follow' | 'yt_lower_third';

export interface StudioBrandState {
  /** Default canvas ratio for Studio / Shorts / other tabs. */
  defaultAspectRatio: AspectRatioValue;
  /** Brand tab preview only — does not reset layout when changed. */
  previewAspectRatio: AspectRatioValue;
  headerEnabled: boolean;
  headerText: string;
  headerOpacity: number;
  footerEnabled: boolean;
  footerText: string;
  footerOpacity: number;
  socialOverlay: SocialOverlayPreset;
  socialHandle: string;
  socialSubtitle: string;
  studioTemplate: 'tiktok_news' | 'tiktok_news_pill';
  layout: StudioLayoutPositions;
  /** Bumps when session images change (triggers re-render). */
  mediaRevision: number;
}

const STORAGE_KEY = 'dubify.studioBrand.v2';

const defaultState = (): StudioBrandState => ({
  defaultAspectRatio: '16:9',
  previewAspectRatio: '9:16',
  headerEnabled: false,
  headerText: '',
  headerOpacity: 85,
  footerEnabled: false,
  footerText: '',
  footerOpacity: 85,
  socialOverlay: 'none',
  socialHandle: '',
  socialSubtitle: '',
  studioTemplate: 'tiktok_news',
  layout: defaultStudioLayout('9:16'),
  mediaRevision: 0,
});

/** Session-only image blobs (not persisted — re-upload after refresh). */
let headerImageFile: File | null = null;
let footerImageFile: File | null = null;
let socialAvatarFile: File | null = null;
let headerImagePreview = '';
let footerImagePreview = '';
let socialAvatarPreview = '';

function loadPersisted(): StudioBrandState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const legacy = localStorage.getItem('dubify.studioBrand.v1');
      if (legacy) {
        const parsed = JSON.parse(legacy) as Partial<StudioBrandState> & { previewAspectRatio?: string };
        const aspect = normalizeAspectRatio(
          parsed.defaultAspectRatio ?? parsed.previewAspectRatio,
          '16:9',
        );
        const preview = normalizeAspectRatio(parsed.previewAspectRatio, aspect);
        return {
          ...defaultState(),
          ...parsed,
          defaultAspectRatio: aspect,
          previewAspectRatio: preview,
          layout: { ...defaultStudioLayout(preview), ...(parsed.layout || {}) },
        };
      }
      return defaultState();
    }
    const parsed = JSON.parse(raw) as Partial<StudioBrandState>;
    const defaultAspect = normalizeAspectRatio(parsed.defaultAspectRatio, '16:9');
    const previewAspect = normalizeAspectRatio(parsed.previewAspectRatio, defaultAspect);
    return {
      ...defaultState(),
      ...parsed,
      defaultAspectRatio: defaultAspect,
      previewAspectRatio: previewAspect,
      layout: { ...defaultStudioLayout(previewAspect), ...(parsed.layout || {}) },
    };
  } catch {
    return defaultState();
  }
}

let state: StudioBrandState = loadPersisted();
const listeners = new Set<() => void>();

function persist() {
  const {
    layout,
    defaultAspectRatio,
    previewAspectRatio,
    headerEnabled,
    headerText,
    headerOpacity,
    footerEnabled,
    footerText,
    footerOpacity,
    socialOverlay,
    socialHandle,
    socialSubtitle,
    studioTemplate,
  } = state;
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      defaultAspectRatio,
      previewAspectRatio,
      headerEnabled,
      headerText,
      headerOpacity,
      footerEnabled,
      footerText,
      footerOpacity,
      socialOverlay,
      socialHandle,
      socialSubtitle,
      studioTemplate,
      layout,
    }),
  );
}

function notify() {
  listeners.forEach((l) => l());
}

export const studioBrandStore = {
  getState: () => state,
  subscribe: (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  setState(patch: Partial<StudioBrandState>) {
    state = { ...state, ...patch };
    if (patch.defaultAspectRatio && isAllowedAspectRatio(patch.defaultAspectRatio)) {
      /* keep layout — user positions are aspect-agnostic enough */
    }
    persist();
    notify();
  },
  setPreviewAspect(aspect: AspectRatioValue) {
    state = { ...state, previewAspectRatio: aspect };
    persist();
    notify();
  },
  setDefaultAspect(aspect: AspectRatioValue) {
    state = { ...state, defaultAspectRatio: aspect };
    persist();
    notify();
  },
  setLayout(layout: StudioLayoutPositions) {
    state = { ...state, layout };
    persist();
    notify();
  },
  getHeaderImage: () => headerImageFile,
  getFooterImage: () => footerImageFile,
  getSocialAvatar: () => socialAvatarFile,
  getHeaderPreview: () => headerImagePreview,
  getFooterPreview: () => footerImagePreview,
  getSocialAvatarPreview: () => socialAvatarPreview,
  setHeaderImage(file: File | null) {
    headerImageFile = file;
    if (headerImagePreview) URL.revokeObjectURL(headerImagePreview);
    headerImagePreview = file ? URL.createObjectURL(file) : '';
    state = { ...state, mediaRevision: state.mediaRevision + 1 };
    notify();
  },
  setFooterImage(file: File | null) {
    footerImageFile = file;
    if (footerImagePreview) URL.revokeObjectURL(footerImagePreview);
    footerImagePreview = file ? URL.createObjectURL(file) : '';
    state = { ...state, mediaRevision: state.mediaRevision + 1 };
    notify();
  },
  setSocialAvatar(file: File | null) {
    socialAvatarFile = file;
    if (socialAvatarPreview) URL.revokeObjectURL(socialAvatarPreview);
    socialAvatarPreview = file ? URL.createObjectURL(file) : '';
    state = { ...state, mediaRevision: state.mediaRevision + 1 };
    notify();
  },
};

export function useDefaultAspectRatio(): AspectRatioValue {
  return useSyncExternalStore(
    studioBrandStore.subscribe,
    () => studioBrandStore.getState().defaultAspectRatio,
    () => studioBrandStore.getState().defaultAspectRatio,
  );
}

export function useStudioBrand() {
  const snap = useSyncExternalStore(
    studioBrandStore.subscribe,
    studioBrandStore.getState,
    studioBrandStore.getState,
  );

  const setBrand = useCallback((patch: Partial<StudioBrandState>) => {
    studioBrandStore.setState(patch);
  }, []);

  const setLayout = useCallback((layout: StudioLayoutPositions) => {
    studioBrandStore.setLayout(layout);
  }, []);

  useEffect(() => {
    return () => {
      /* previews revoked on next set */
    };
  }, []);

  return {
    brand: snap,
    setBrand,
    setLayout,
    setPreviewAspect: studioBrandStore.setPreviewAspect,
    setDefaultAspect: studioBrandStore.setDefaultAspect,
    headerImage: studioBrandStore.getHeaderImage(),
    footerImage: studioBrandStore.getFooterImage(),
    socialAvatar: studioBrandStore.getSocialAvatar(),
    headerImagePreview: studioBrandStore.getHeaderPreview(),
    footerImagePreview: studioBrandStore.getFooterPreview(),
    socialAvatarPreview: studioBrandStore.getSocialAvatarPreview(),
    setHeaderImage: studioBrandStore.setHeaderImage,
    setFooterImage: studioBrandStore.setFooterImage,
    setSocialAvatar: studioBrandStore.setSocialAvatar,
  };
}

/** Append branding + layout fields to Studio / Shorts FormData. */
export function appendStudioBrandToFormData(formData: FormData) {
  const b = studioBrandStore.getState();
  formData.append('header_enabled', b.headerEnabled ? 'true' : 'false');
  formData.append('footer_enabled', b.footerEnabled ? 'true' : 'false');
  if (b.headerEnabled) {
    formData.append('header_text', b.headerText);
    formData.append('header_opacity', String(b.headerOpacity / 100));
    const hi = studioBrandStore.getHeaderImage();
    if (hi) formData.append('header_image', hi);
  }
  if (b.footerEnabled) {
    formData.append('footer_text', b.footerText);
    formData.append('footer_opacity', String(b.footerOpacity / 100));
    const fi = studioBrandStore.getFooterImage();
    if (fi) formData.append('footer_image', fi);
  }
  formData.append('social_overlay', b.socialOverlay);
  if (b.socialHandle.trim()) formData.append('social_handle', b.socialHandle.trim());
  if (b.socialSubtitle.trim()) formData.append('social_subtitle', b.socialSubtitle.trim());
  const av = studioBrandStore.getSocialAvatar();
  if (av) formData.append('social_avatar', av);
  formData.append('header_y_pct', String(b.layout.headerYPct));
  formData.append('footer_y_pct', String(b.layout.footerYPct));
  formData.append('social_left_pct', String(b.layout.socialLeftPct));
  formData.append('social_bottom_pct', String(b.layout.socialBottomPct));
  formData.append('caption_y_pct', String(b.layout.captionYPct));
}
