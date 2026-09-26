/**
 * AI Preferences, UI Language & Theme Context.
 * Manages:
 * 1. UI Language ('vi' | 'en') - default 'vi' (Persisted in 'sourcecheck_ui_language')
 * 2. AI Response Language ('vi' | 'en') - default 'vi' (Persisted in 'sourcecheck_ai_language')
 * 3. Theme mode ('light' | 'dark') - default 'light' (Persisted in 'sourcecheck_theme')
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { UILanguage, TranslationKey, translate } from '../i18n';

export type { UILanguage };
export type AILanguage = 'vi' | 'en';
export type ThemeMode = 'light' | 'dark';
export type FontSize = 'small' | 'medium' | 'large';

export const UI_LANGUAGE_STORAGE_KEY = 'sourcecheck_ui_language';
export const AI_LANGUAGE_STORAGE_KEY = 'sourcecheck_ai_language';
export const THEME_STORAGE_KEY = 'sourcecheck_theme';
export const SHOW_SOURCES_STORAGE_KEY = 'sourcecheck_show_sources';
export const SHOW_VERIFICATION_STORAGE_KEY = 'sourcecheck_show_verification';
export const FONT_SIZE_STORAGE_KEY = 'sourcecheck_font_size';

export interface AIPreferencesContextType {
  // UI Language
  uiLanguage: UILanguage;
  setUILanguage: (lang: UILanguage) => void;
  // AI Response Language
  aiLanguage: AILanguage;
  setAILanguage: (lang: AILanguage) => void;
  // Theme Mode
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  fontSize: FontSize;
  setFontSize: (size: FontSize) => void;
  // Frontend presentation preferences
  showSources: boolean;
  setShowSources: (enabled: boolean) => void;
  showVerification: boolean;
  setShowVerification: (enabled: boolean) => void;
  // Active Chat Title (for sticky AppHeader display)
  activeChatTitle: string | null;
  setActiveChatTitle: (title: string | null) => void;
  // Translation helper
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const defaultContextValue: AIPreferencesContextType = {
  uiLanguage: 'vi',
  setUILanguage: () => {},
  aiLanguage: 'vi',
  setAILanguage: () => {},
  theme: 'light',
  setTheme: () => {},
  toggleTheme: () => {},
  fontSize: 'medium',
  setFontSize: () => {},
  showSources: true,
  setShowSources: () => {},
  showVerification: true,
  setShowVerification: () => {},
  activeChatTitle: null,
  setActiveChatTitle: () => {},
  t: (key, params) => translate(key, 'vi', params),
};

export const AIPreferencesContext = createContext<AIPreferencesContextType>(defaultContextValue);

export const AIPreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // 1. UI Language State (Persisted, default 'vi')
  const [uiLanguage, setUILanguageState] = useState<UILanguage>(() => {
    try {
      const stored = localStorage.getItem(UI_LANGUAGE_STORAGE_KEY);
      if (stored === 'en' || stored === 'vi') {
        return stored;
      }
    } catch {
      // Ignore localStorage access errors
    }
    return 'vi';
  });

  // 2. AI Response Language State (Persisted, default 'vi')
  const [aiLanguage, setAILanguageState] = useState<AILanguage>(() => {
    try {
      const stored = localStorage.getItem(AI_LANGUAGE_STORAGE_KEY);
      if (stored === 'en' || stored === 'vi') {
        return stored;
      }
    } catch {
      // Ignore localStorage access errors
    }
    return 'vi';
  });

  // 3. Theme State (Persisted, default 'light')
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        return stored;
      }
      // Check system preference if no explicit choice
      if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    } catch {
      // Ignore localStorage access errors
    }
    return 'light';
  });

  const [fontSize, setFontSizeState] = useState<FontSize>(() => {
    try {
      const stored = localStorage.getItem(FONT_SIZE_STORAGE_KEY);
      if (stored === 'small' || stored === 'medium' || stored === 'large') return stored;
    } catch {
      // Ignore localStorage access errors
    }
    return 'medium';
  });

  const setFontSize = useCallback((size: FontSize) => {
    setFontSizeState(size);
    try {
      localStorage.setItem(FONT_SIZE_STORAGE_KEY, size);
    } catch {
      // Ignore
    }
  }, []);
  const setUILanguage = useCallback((lang: UILanguage) => {
    setUILanguageState(lang);
    try {
      localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, lang);
    } catch {
      // Ignore
    }
  }, []);

  const setAILanguage = useCallback((lang: AILanguage) => {
    setAILanguageState(lang);
    try {
      localStorage.setItem(AI_LANGUAGE_STORAGE_KEY, lang);
    } catch {
      // Ignore
    }
  }, []);

  const setTheme = useCallback((newTheme: ThemeMode) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch {
      // Ignore
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      try {
        localStorage.setItem(THEME_STORAGE_KEY, next);
      } catch {
        // Ignore
      }
      return next;
    });
  }, []);

  // Translation helper bound to current uiLanguage
  const t = useCallback(
    (key: TranslationKey, params?: Record<string, string | number>) => {
      return translate(key, uiLanguage, params);
    },
    [uiLanguage]
  );

  // 4. Frontend presentation preferences (persisted locally)
  const [showSources, setShowSourcesState] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SHOW_SOURCES_STORAGE_KEY) !== 'false';
    } catch {
      return true;
    }
  });

  const [showVerification, setShowVerificationState] = useState<boolean>(() => {
    try {
      return localStorage.getItem(SHOW_VERIFICATION_STORAGE_KEY) !== 'false';
    } catch {
      return true;
    }
  });

  const setShowSources = useCallback((enabled: boolean) => {
    setShowSourcesState(enabled);
    try {
      localStorage.setItem(SHOW_SOURCES_STORAGE_KEY, String(enabled));
    } catch {
      // Ignore
    }
  }, []);

  const setShowVerification = useCallback((enabled: boolean) => {
    setShowVerificationState(enabled);
    try {
      localStorage.setItem(SHOW_VERIFICATION_STORAGE_KEY, String(enabled));
    } catch {
      // Ignore
    }
  }, []);

  // 5. Active Chat Title State
  const [activeChatTitle, setActiveChatTitle] = useState<string | null>(null);

  // Sync DOM data-theme attribute with state
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme]);

  // Sync document typography with the persisted preference.
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-font-size', fontSize);
    }
  }, [fontSize]);
  // Sync DOM lang attribute with uiLanguage
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('lang', uiLanguage);
    }
  }, [uiLanguage]);

  return (
    <AIPreferencesContext.Provider
      value={{
        uiLanguage,
        setUILanguage,
        aiLanguage,
        setAILanguage,
        theme,
        setTheme,
        toggleTheme,
        fontSize,
        setFontSize,
        showSources,
        setShowSources,
        showVerification,
        setShowVerification,
        activeChatTitle,
        setActiveChatTitle,
        t,
      }}
    >
      {children}
    </AIPreferencesContext.Provider>
  );
};

export const useAIPreferences = (): AIPreferencesContextType => {
  return useContext(AIPreferencesContext);
};
