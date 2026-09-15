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

export const UI_LANGUAGE_STORAGE_KEY = 'sourcecheck_ui_language';
export const AI_LANGUAGE_STORAGE_KEY = 'sourcecheck_ai_language';
export const THEME_STORAGE_KEY = 'sourcecheck_theme';

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

  // Sync DOM data-theme attribute with state
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme]);

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
