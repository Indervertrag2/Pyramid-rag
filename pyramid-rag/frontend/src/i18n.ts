import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';
import deTranslations from './locales/de.json';

// English translations (fallback)
const enTranslations = {
  common: {
    appTitle: "Pyramid RAG Platform",
    loading: "Loading...",
    error: "Error",
    success: "Success",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    search: "Search",
    filter: "Filter",
    close: "Close",
    back: "Back",
    next: "Next",
    submit: "Submit",
    download: "Download",
    upload: "Upload",
    refresh: "Refresh",
    yes: "Yes",
    no: "No"
  },
  auth: {
    login: "Login",
    logout: "Logout",
    email: "Email",
    password: "Password",
    rememberMe: "Remember me",
    forgotPassword: "Forgot password?",
    loginTitle: "Sign in to Pyramid RAG",
    loginSuccess: "Successfully logged in",
    loginError: "Login failed",
    invalidCredentials: "Invalid email or password",
    changePassword: "Change password",
    currentPassword: "Current password",
    newPassword: "New password",
    confirmPassword: "Confirm password",
    passwordChanged: "Password changed successfully"
  },
  // ... rest of English translations (mirroring German structure)
};

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: {
        translation: deTranslations
      },
      en: {
        translation: enTranslations
      }
    },
    lng: 'de', // Default language
    fallbackLng: 'en',
    debug: false,

    interpolation: {
      escapeValue: false // React already escapes values
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage']
    }
  });

export default i18n;