import React, { useState } from 'react';
import axios from 'axios';

import apiClient from '../services/apiClient';

const LoginSimple: React.FC = () => {
  const [email, setEmail] = useState('admin@pyramid-computer.de');
  const [password, setPassword] = useState('PyramidAdmin2024!');
  const [error, setError] = useState('');
  const [result, setResult] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setResult('');

    try {
      console.log('Attempting login with:', { email, password });

      const { data } = await apiClient.post('/api/v1/auth/login', { email, password });
      console.log('Response:', data);

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      setResult('Login successful! Token: ' + data.access_token.substring(0, 20) + '...');

      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 2000);
    } catch (err: unknown) {
      console.error('Login error:', err);
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message || 'Unknown error'
        : (err as Error).message;
      setError('Login failed: ' + message);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '400px', margin: '50px auto' }}>
      <h1>Pyramid RAG Login</h1>

      {error && (
        <div style={{ color: 'red', marginBottom: '10px' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ color: 'green', marginBottom: '10px' }}>
          {result}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '10px' }}>
          <label>
            Email:<br />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
            />
          </label>
        </div>

        <div style={{ marginBottom: '10px' }}>
          <label>
            Password:<br />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
            />
          </label>
        </div>

        <button type="submit" style={{ padding: '10px 20px' }}>
          Login
        </button>
      </form>

      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        <p>Default credentials:</p>
        <p>Email: admin@pyramid-computer.de</p>
        <p>Password: PyramidAdmin2024!</p>
      </div>
    </div>
  );
};

export default LoginSimple;
