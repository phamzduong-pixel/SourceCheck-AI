import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute, PublicOnlyRoute } from './components/auth/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { OAuthCallbackPage } from './pages/OAuthCallbackPage';
import { ProtectedPlaceholderPage } from './pages/ProtectedPlaceholderPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public-only routes: redirect to protected entry point if already authenticated */}
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

          {/* OAuth callback route for Google OAuth redirects */}
          <Route path="/auth/callback" element={<OAuthCallbackPage />} />
          <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

          {/* Protected routes: require authentication, otherwise redirect to /login */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ProtectedPlaceholderPage />
              </ProtectedRoute>
            }
          />

          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
