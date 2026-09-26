import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AIPreferencesProvider } from '../context/AIPreferencesContext';
import { AuthProvider } from '../context/AuthContext';
import { TOKEN_STORAGE_KEY } from '../services/auth';
import { ProfilePage } from '../pages/ProfilePage';
import { SettingsPage } from '../pages/SettingsPage';

describe('Settings page', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('persists theme and response presentation preferences', () => {
    render(
      <MemoryRouter>
        <AIPreferencesProvider>
          <SettingsPage />
        </AIPreferencesProvider>
      </MemoryRouter>,
    );

    expect(screen.getByTestId('settings-theme-light')).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByTestId('settings-theme-dark'));
    expect(localStorage.getItem('sourcecheck_theme')).toBe('dark');
    expect(screen.getByTestId('settings-theme-dark')).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByTestId('settings-font-size-large'));
    expect(localStorage.getItem('sourcecheck_font_size')).toBe('large');

    fireEvent.click(screen.getByTestId('settings-show-sources'));
    fireEvent.click(screen.getByTestId('settings-show-verification'));
    expect(localStorage.getItem('sourcecheck_show_sources')).toBe('false');
    expect(localStorage.getItem('sourcecheck_show_verification')).toBe('false');
  });
  it('persists font-size and saves the real profile API response', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'profile-token');
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes('/auth/me') && (!init || init.method === 'GET')) {
        return new Response(JSON.stringify({
          success: true,
          data: {
            id: 'user-1', email: 'user@gmail.com', full_name: 'Initial Name',
            role: 'user', is_active: true, avatar_url: null, phone_number: null,
            auth_provider: 'google', created_at: '2026-01-01T00:00:00Z',
          },
        }), { status: 200, headers: { 'content-type': 'application/json' } });
      }
      if (url.includes('/auth/me') && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        return new Response(JSON.stringify({
          success: true,
          data: {
            id: 'user-1', email: 'user@gmail.com', full_name: body.full_name,
            role: 'user', is_active: true, avatar_url: body.avatar_url, phone_number: body.phone_number,
            auth_provider: 'google', created_at: '2026-01-01T00:00:00Z',
          },
        }), { status: 200, headers: { 'content-type': 'application/json' } });
      }
      return new Response('{}', { status: 404 });
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <AIPreferencesProvider>
            <ProfilePage />
          </AIPreferencesProvider>
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId('profile-full-name')).toHaveValue('Initial Name'));
    fireEvent.change(screen.getByTestId('profile-full-name'), { target: { value: 'Updated Name' } });
    fireEvent.change(screen.getByTestId('profile-phone'), { target: { value: '+84901234567' } });
    fireEvent.click(screen.getByTestId('profile-save'));
    await waitFor(() => expect(screen.getByTestId('profile-feedback')).toBeInTheDocument());

    expect(screen.getByTestId('profile-email')).toHaveValue('user@gmail.com');
  });
});
