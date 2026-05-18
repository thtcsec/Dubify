import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { en, type Locale } from './locales/en';
import { vi } from './locales/vi';

export type LocaleCode = 'en' | 'vi';

const STORAGE_KEY = 'dubify_locale';

const catalogs: Record<LocaleCode, Locale> = { en, vi };

type I18nContextValue = {
  locale: LocaleCode;
  t: Locale;
  setLocale: (code: LocaleCode) => void;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function readStoredLocale(): LocaleCode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'vi') return stored;
  } catch {
    /* ignore */
  }
  return 'vi';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleCode>(readStoredLocale);

  const setLocale = useCallback((code: LocaleCode) => {
    setLocaleState(code);
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(
    () => ({
      locale,
      t: catalogs[locale],
      setLocale,
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return ctx;
}
