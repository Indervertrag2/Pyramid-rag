import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Container,
  Fade
} from '@mui/material';
import { useAuth } from '../App'; // Import from App.tsx where it's defined
import { useNavigate } from 'react-router-dom';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const Login: React.FC = () => {
  const [email, setEmail] = useState('admin@pyramid-computer.de');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      setLoginSuccess(true);
      // Show success message for 2 seconds before redirect
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } catch (err) {
      setError('Anmeldung fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.');
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={8}
          sx={{
            p: 4,
            width: '100%',
            maxWidth: 400,
            animation: 'slideIn 0.5s ease',
            '@keyframes slideIn': {
              from: {
                opacity: 0,
                transform: 'translateY(-20px)',
              },
              to: {
                opacity: 1,
                transform: 'translateY(0)',
              },
            },
          }}
        >
          {loginSuccess ? (
            <Fade in={loginSuccess}>
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <CheckCircleIcon sx={{ fontSize: 60, color: '#4caf50', mb: 2 }} />
                <Typography variant="h5" color="success.main" gutterBottom>
                  Anmeldung erfolgreich!
                </Typography>
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  Sie werden zum Dashboard weitergeleitet...
                </Typography>
                <CircularProgress size={24} sx={{ mt: 2 }} />
              </Box>
            </Fade>
          ) : (
            <>
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <Typography
                  variant="h4"
                  component="h1"
                  gutterBottom
                  sx={{
                    color: '#003d7a',
                    fontWeight: 600,
                    fontSize: '28px',
                  }}
                >
                  Pyramid RAG Platform
                </Typography>
                <Typography variant="subtitle1" sx={{ color: '#666', fontSize: '14px' }}>
                  Enterprise KI-Dokumentenmanagement
                </Typography>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="E-Mail Adresse"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  margin="normal"
                  required
                  disabled={loading}
                  autoComplete="email"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '&:hover fieldset': {
                        borderColor: '#003d7a',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#003d7a',
                      },
                    },
                  }}
                />

                <TextField
                  fullWidth
                  label="Passwort"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  margin="normal"
                  required
                  disabled={loading}
                  autoComplete="current-password"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      '&:hover fieldset': {
                        borderColor: '#003d7a',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: '#003d7a',
                      },
                    },
                  }}
                />

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading}
                  sx={{
                    mt: 3,
                    mb: 2,
                    height: 48,
                    fontSize: '16px',
                    fontWeight: 500,
                    backgroundColor: '#003d7a',
                    '&:hover': {
                      backgroundColor: '#002d5a',
                      boxShadow: '0 4px 12px rgba(0, 61, 122, 0.3)',
                    },
                    '&:disabled': {
                      backgroundColor: '#ccc',
                    },
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    'Anmelden'
                  )}
                </Button>
              </form>

              <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                <Typography variant="body2" sx={{ color: '#333', fontWeight: 500, mb: 1 }}>
                  <strong>Demo-Zugangsdaten:</strong>
                </Typography>
                <Typography variant="body2" sx={{ color: '#666' }}>
                  E-Mail: admin@pyramid-computer.de<br />
                  Passwort: PyramidAdmin2024!
                </Typography>
              </Box>
            </>
          )}
        </Paper>
      </Container>
    </Box>
  );
};

export default Login;