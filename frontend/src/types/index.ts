/**
 * Centralized export of all TypeScript models and interfaces for SourceCheck AI.
 */

export * from './common';
export * from './system';
export * from './document';
export * from './search';
export * from './verification';
export * from './qa';
export * from './dashboard';
export {
  type User,
  type LoginCredentials,
  type RegisterCredentials,
  type TokenResponse,
  type GoogleLoginResponse,
  type AuthState,
} from './auth';
