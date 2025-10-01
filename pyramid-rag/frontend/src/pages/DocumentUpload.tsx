import React, { useState, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  TextField,
  Chip,
  IconButton,
  Alert,
  LinearProgress,
  Grid,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  ArrowBack as ArrowBackIcon,
  InsertDriveFile as FileIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
// import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

interface FileUpload {
  file: File;
  id: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

interface FileMetadata {
  tags: string[];
  description: string;
  status: 'draft' | 'published' | 'archived';
}

const DocumentUpload: React.FC = () => {
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [metadata, setMetadata] = useState<FileMetadata>({
    tags: [],
    description: '',
    status: 'published'
  });
  const [tagInput, setTagInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  // const [uploadError, setUploadError] = useState<string>(''); // Removed unused variable
  const [uploadError] = useState<string>('');

  const navigate = useNavigate();
  // const { user } = useAuth(); // Removed unused variable
  const { darkMode } = useTheme();

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const addFiles = (newFiles: File[]) => {
    const fileUploads: FileUpload[] = newFiles.map(file => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      progress: 0,
      status: 'pending'
    }));

    setFiles(prev => [...prev, ...fileUploads]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const addTag = () => {
    if (tagInput.trim() && !metadata.tags.includes(tagInput.trim())) {
      setMetadata(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setMetadata(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }));
  };

  const uploadFile = async (fileUpload: FileUpload) => {
    const formData = new FormData();
    formData.append('file', fileUpload.file);
    formData.append('description', metadata.description);
    formData.append('tags', JSON.stringify(metadata.tags));
    formData.append('status', metadata.status);

    try {
      setFiles(prev =>
        prev.map(f =>
          f.id === fileUpload.id
            ? { ...f, status: 'uploading', progress: 0 }
            : f
        )
      );

      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:18000/api/v1/documents/upload-simple', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData
      });

      if (response.ok) {
        setFiles(prev =>
          prev.map(f =>
            f.id === fileUpload.id
              ? { ...f, status: 'success', progress: 100 }
              : f
          )
        );
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      setFiles(prev =>
        prev.map(f =>
          f.id === fileUpload.id
            ? { ...f, status: 'error', error: 'Upload fehlgeschlagen' }
            : f
        )
      );
    }
  };

  const uploadAll = async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');

    for (const fileUpload of pendingFiles) {
      await uploadFile(fileUpload);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box sx={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: darkMode ? '#1a1a1a' : '#f7f7f8'
    }}>
      {/* Header */}
      <AppBar position="static" elevation={0} sx={{
        bgcolor: darkMode ? '#2c2c2c' : 'white',
        borderBottom: darkMode ? '1px solid #444' : '1px solid #e0e0e0'
      }}>
        <Toolbar>
          <IconButton
            edge="start"
            onClick={() => navigate('/dashboard')}
            sx={{ mr: 2, color: 'text.primary' }}
          >
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, color: 'text.primary', fontWeight: 500 }}>
            Dokumente hochladen
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ py: 3, flexGrow: 1 }}>
        <Grid container spacing={3}>
          {/* Upload Area */}
          <Grid item xs={12} md={8}>
            <Paper
              sx={{
                p: 4,
                border: isDragging ? '2px dashed #10a37f' : '2px dashed #e0e0e0',
                borderRadius: '12px',
                bgcolor: isDragging
                  ? (darkMode ? 'rgba(16, 163, 127, 0.1)' : 'rgba(16, 163, 127, 0.05)')
                  : (darkMode ? '#2c2c2c' : 'white'),
                textAlign: 'center',
                transition: 'all 0.3s ease'
              }}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
            >
              <UploadIcon sx={{ fontSize: 64, color: '#10a37f', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Dateien hier ablegen oder durchsuchen
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Unterstützte Formate: PDF, Word, Excel, PowerPoint, Text und mehr
                <br />
                Max. Dateigröße: 1 GB
              </Typography>

              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                id="file-upload"
                accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.rtf,.odt,.ods,.odp"
              />
              <label htmlFor="file-upload">
                <Button
                  variant="contained"
                  component="span"
                  sx={{
                    bgcolor: '#10a37f',
                    '&:hover': { bgcolor: '#0e8968' },
                    textTransform: 'none',
                    px: 4
                  }}
                >
                  Dateien auswählen
                </Button>
              </label>
            </Paper>

            {/* File List */}
            {files.length > 0 && (
              <Paper sx={{ mt: 3, p: 2, bgcolor: darkMode ? '#2c2c2c' : 'white' }}>
                <Typography variant="h6" gutterBottom>
                  Ausgewählte Dateien ({files.length})
                </Typography>

                {files.map((fileUpload) => (
                  <Card key={fileUpload.id} sx={{ mb: 2, bgcolor: darkMode ? '#383838' : '#f9f9f9' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <FileIcon color="primary" />
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="subtitle1" noWrap>
                            {fileUpload.file.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatFileSize(fileUpload.file.size)} • {fileUpload.file.type}
                          </Typography>
                        </Box>

                        {fileUpload.status === 'uploading' && (
                          <Box sx={{ width: '100px' }}>
                            <LinearProgress
                              variant="determinate"
                              value={fileUpload.progress}
                              sx={{ height: 8, borderRadius: 4 }}
                            />
                          </Box>
                        )}

                        <Chip
                          label={fileUpload.status === 'pending' ? 'Bereit' :
                                 fileUpload.status === 'uploading' ? 'Upload...' :
                                 fileUpload.status === 'success' ? 'Erfolgreich' : 'Fehler'}
                          color={fileUpload.status === 'success' ? 'success' :
                                 fileUpload.status === 'error' ? 'error' : 'default'}
                          size="small"
                        />

                        <IconButton onClick={() => removeFile(fileUpload.id)} size="small">
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </CardContent>
                  </Card>
                ))}

                <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
                  <Button
                    variant="contained"
                    onClick={uploadAll}
                    disabled={files.every(f => f.status !== 'pending')}
                    sx={{
                      bgcolor: '#10a37f',
                      '&:hover': { bgcolor: '#0e8968' },
                      textTransform: 'none'
                    }}
                  >
                    Alle hochladen ({files.filter(f => f.status === 'pending').length})
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => setFiles([])}
                    sx={{ textTransform: 'none' }}
                  >
                    Liste leeren
                  </Button>
                </Box>
              </Paper>
            )}
          </Grid>

          {/* Metadata Panel */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, bgcolor: darkMode ? '#2c2c2c' : 'white' }}>
              <Typography variant="h6" gutterBottom>
                Metadaten
              </Typography>

              {/* Description */}
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Beschreibung"
                value={metadata.description}
                onChange={(e) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
                sx={{ mb: 3 }}
              />

              {/* Status */}
              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={metadata.status}
                  label="Status"
                  onChange={(e) => setMetadata(prev => ({
                    ...prev,
                    status: e.target.value as 'draft' | 'published' | 'archived'
                  }))}
                >
                  <MenuItem value="draft">Entwurf</MenuItem>
                  <MenuItem value="published">Veröffentlicht</MenuItem>
                  <MenuItem value="archived">Archiviert</MenuItem>
                </Select>
              </FormControl>

              {/* Tags */}
              <Typography variant="subtitle1" gutterBottom>
                Tags
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <TextField
                  size="small"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="Tag hinzufügen"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  sx={{ flexGrow: 1 }}
                />
                <Button onClick={addTag} variant="outlined" size="small">
                  +
                </Button>
              </Box>

              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {metadata.tags.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    onDelete={() => removeTag(tag)}
                    size="small"
                    color="primary"
                  />
                ))}
              </Box>

              {uploadError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {uploadError}
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default DocumentUpload;