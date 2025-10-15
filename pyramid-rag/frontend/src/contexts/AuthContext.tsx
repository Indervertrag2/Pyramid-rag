import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

import type { User } from '../types';
import axios from 'axios';
import apiClient from '../services/apiClient';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setIsLoading(false);
      return;
    }

    const fetchCurrentUser = async () => {
      try {
        const { data } = await apiClient.get('/api/v1/auth/me');
        setUser({
          id: data.id,
          email: data.email,
          username: data.username,
          full_name: data.full_name || data.username,
          primary_department: data.primary_department || 'Unknown',
          is_superuser: data.is_superuser || false,
          roles: data.roles || [],
        });
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCurrentUser();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const { data } = await apiClient.post('/api/v1/auth/login', { email, password });

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      if (data.user) {
        setUser({
          id: data.user.id,
          email: data.user.email,
          username: data.user.username,
          full_name: data.user.full_name || data.user.username,
          primary_department: data.user.primary_department || 'Unknown',
          is_superuser: data.user.is_superuser || false,
          roles: data.user.roles || [],
        });
      }
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
        throw new Error(detail || 'Login failed');
      }
      throw error instanceof Error ? error : new Error('Login failed');
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const token = localStorage.getItem('access_token');

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
