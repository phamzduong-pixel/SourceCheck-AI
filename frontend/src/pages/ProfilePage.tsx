import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useAIPreferences } from '../hooks/useAIPreferences';
import '../styles/settings.css';

const MAX_AVATAR_BYTES = 1.5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, updateUserProfile } = useAuth();
  const { t } = useAIPreferences();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number || '');
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '');
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    setFullName(user?.full_name || '');
    setPhoneNumber(user?.phone_number || '');
    setAvatarUrl(user?.avatar_url || '');
  }, [user]);

  const handleAvatarChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type) || file.size > MAX_AVATAR_BYTES) {
      setFeedback({ type: 'error', message: t('settings.invalidImage') });
      event.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setAvatarUrl(reader.result);
        setFeedback(null);
      }
    };
    reader.onerror = () => setFeedback({ type: 'error', message: t('settings.invalidImage') });
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!fullName.trim()) {
      setFeedback({ type: 'error', message: t('settings.saveError') });
      return;
    }
    setIsSaving(true);
    setFeedback(null);
    try {
      await updateUserProfile({
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim() || null,
        avatar_url: avatarUrl || null,
      });
      setFeedback({ type: 'success', message: t('settings.saveSuccess') });
    } catch {
      setFeedback({ type: 'error', message: t('settings.saveError') });
    } finally {
      setIsSaving(false);
    }
  };

  const initials = (fullName || user?.email || 'U')
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="settings-page profile-page" data-testid="profile-page">
      <div className="settings-header">
        <button type="button" className="settings-back-button" onClick={() => navigate(-1)} data-testid="profile-back">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
          <span>{t('settings.back')}</span>
        </button>
        <div>
          <h1>{t('settings.profile')}</h1>
          <p>{t('settings.profileSubtitle')}</p>
        </div>
      </div>

      <form className="profile-form settings-section" onSubmit={handleSubmit}>
        <div className="profile-avatar-row">
          <div className="profile-avatar-preview" aria-hidden="true">
            {avatarUrl ? <img src={avatarUrl} alt="" /> : initials}
          </div>
          <div className="profile-avatar-copy">
            <h2>{t('settings.avatar')}</h2>
            <p>{t('settings.avatarHint')}</p>
            <label className="profile-file-button" htmlFor="profile-avatar-input">
              {t('settings.chooseImage')}
              <input
                id="profile-avatar-input"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleAvatarChange}
                data-testid="profile-avatar-input"
              />
            </label>
          </div>
        </div>

        <div className="profile-fields">
          <label className="profile-field">
            <span>{t('settings.fullName')}</span>
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              autoComplete="name"
              maxLength={255}
              data-testid="profile-full-name"
            />
          </label>
          <label className="profile-field">
            <span>{t('settings.email')}</span>
            <input value={user?.email || ''} readOnly disabled data-testid="profile-email" />
          </label>
          <label className="profile-field">
            <span>{t('settings.phone')}</span>
            <input
              value={phoneNumber}
              onChange={(event) => setPhoneNumber(event.target.value)}
              autoComplete="tel"
              maxLength={32}
              data-testid="profile-phone"
            />
          </label>
        </div>

        <div className="profile-actions">
          {feedback && (
            <p className={`profile-feedback ${feedback.type}`} data-testid="profile-feedback" role={feedback.type === 'error' ? 'alert' : 'status'}>
              {feedback.message}
            </p>
          )}
          <button type="submit" className="settings-primary-button" disabled={isSaving} data-testid="profile-save">
            {isSaving ? t('common.loading') : t('settings.saveProfile')}
          </button>
        </div>
      </form>
    </div>
  );
};