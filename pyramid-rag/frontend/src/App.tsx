import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ChatInterface from './pages/ChatInterface';
// import DocumentUpload from './pages/DocumentUpload';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';

// Re-export useAuth for backward compatibility
export { useAuth } from './contexts/AuthContext';

// Protected Route
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const token = localStorage.getItem('access_token');

  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Check both user and token for authentication
  if (!user && !token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Admin Protected Route
const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const token = localStorage.getItem('access_token');

  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Check both user and token for authentication
  if (!user && !token) {
    return <Navigate to="/login" replace />;
  }

  // Check if user is admin
  const isAdmin = user?.is_superuser || user?.roles?.includes('admin');
  if (!isAdmin) {
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
};

// Login Page Wrapper
const LoginPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const token = localStorage.getItem('access_token');

  useEffect(() => {
    // Redirect if already logged in (check token too)
    if (user || token) {
      navigate('/chat');
    }
  }, [user, token, navigate]);

  return <Login />;
};

function App() {
  return (
    <ThemeProvider>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <ChatInterface />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <AdminRoute>
                  <Dashboard />
                </AdminRoute>
              }
            />
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;