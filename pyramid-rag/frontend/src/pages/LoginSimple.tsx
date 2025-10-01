import React, { useState } from 'react';

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

      const response = await fetch('http://localhost:18000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      console.log('Response:', data);

      if (!response.ok) {
        setError('Login failed: ' + (data.detail || 'Unknown error'));
        return;
      }

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      setResult('Login successful! Token: ' + data.access_token.substring(0, 20) + '...');

      // Redirect after 2 seconds
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 2000);

    } catch (err: any) {
      console.error('Login error:', err);
      setError('Network error: ' + (err.message || 'Unknown error'));
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