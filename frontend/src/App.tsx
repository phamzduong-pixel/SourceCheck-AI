import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AIPreferencesProvider } from './context/AIPreferencesContext';
import { ProtectedRoute, PublicOnlyRoute } from './components/auth/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { OAuthCallbackPage } from './pages/OAuthCallbackPage';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { FactCheckPage } from './pages/FactCheckPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { ResearchChatPage } from './pages/ResearchChatPage';
import { SearchPage } from './pages/SearchPage';
import { VerificationHistoryPage } from './pages/VerificationHistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { ProfilePage } from './pages/ProfilePage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AIPreferencesProvider>
          <Routes>
          {/* Public-only routes: redirect to dashboard if already authenticated */}
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicOnlyRoute>
                <RegisterPage />
              </PublicOnlyRoute>
            }
          />

          {/* OAuth callback routes for Google OAuth redirects */}
          <Route path="/auth/callback" element={<OAuthCallbackPage />} />
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

          {/* Protected routes wrapped in AppLayout: require authentication */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<ResearchChatPage />} />
            <Route path="/chat" element={<ResearchChatPage />} />
            <Route path="/chat/:conversationId" element={<ResearchChatPage />} />
            <Route path="/qa" element={<ResearchChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/fact-check" element={<FactCheckPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/verification-history" element={<VerificationHistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </AIPreferencesProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}