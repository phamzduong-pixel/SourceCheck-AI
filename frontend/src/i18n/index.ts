import { TranslationKey, UILanguage, TranslationDictionary } from './types';
import { viTranslations } from './translations/vi';
import { enTranslations } from './translations/en';

export * from './types';

const dictionaries: Record<UILanguage, TranslationDictionary> = {
  vi: viTranslations,
  en: enTranslations,
};

/**
 * Translates a key for a given language, with optional template parameter interpolation.
 * Example: t('qa.supportedClaims', 'vi') -> 'Được xác nhận'
 */
export function translate(
  key: TranslationKey,
  lang: UILanguage = 'vi',
  params?: Record<string, string | number>
): string {
  const dict = dictionaries[lang] || dictionaries.vi;
  let text = dict[key] || dictionaries.en[key] || key;

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    });
  }

  return text;
}
