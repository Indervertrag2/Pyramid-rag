import React, { useState } from 'react';

import {

  Button,

  CircularProgress,

  Alert,

  Box,

  Typography,

  LinearProgress,

} from '@mui/material';

import { CloudUpload } from '@mui/icons-material';



import axios from 'axios';

import apiClient from '../services/apiClient';



interface SimpleUploadProps {

  onUploadComplete?: (documents: any[]) => void;

  onClose?: () => void;

  fileScope?: 'company' | 'chat';  // File scope from parent component

  sessionId?: string;  // Required for chat-scoped uploads

}



const SimpleUpload: React.FC<SimpleUploadProps> = ({ onUploadComplete, onClose, fileScope = 'company', sessionId }) => {

  const [uploading, setUploading] = useState(false);

  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');

  const [uploadMessage, setUploadMessage] = useState('');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);



  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {

    const file = event.target.files?.[0];

    if (file) {

      setSelectedFile(file);

      setUploadStatus('idle');

      setUploadMessage('');

    }

  };



  const handleUpload = async () => {

    if (!selectedFile) {

      setUploadMessage('Bitte wählen Sie eine Datei aus');

      return;

    }



    setUploading(true);

    setUploadStatus('uploading');

    setUploadMessage('Datei wird hochgeladen...');



    // Validate required parameters for chat-scoped uploads

    if (fileScope === 'chat' && !sessionId) {

      setUploadStatus('error');

      setUploadMessage('Session ID erforderlich für Chat-Uploads');

      setUploading(false);

      return;

    }



    const formData = new FormData();

    formData.append('file', selectedFile);

    formData.append('scope', fileScope === 'company' ? 'GLOBAL' : 'CHAT');

    if (sessionId && fileScope === 'chat') {

      formData.append('session_id', sessionId);

    }



    try {

      const { data } = await apiClient.post('/api/v1/documents/upload', formData, {

        headers: {

          'Content-Type': 'multipart/form-data',

        },

      });



      if (data.duplicate) {

        setUploadStatus('error');

        setUploadMessage(`dY", Datei bereits vorhanden: "${data.filename}"`);

      } else {

        setUploadStatus('success');

        const processingInfo = data.processing_time ? ` (${data.processing_time.toFixed(1)}s)` : '';

        const scopeInfo = data.scope === 'GLOBAL' ? 'Firmendatenbank' : 'Chat-Kontext';

        const chunksInfo = data.chunks_created > 0 ? `, ${data.chunks_created} Chunks erstellt` : '';



        setUploadMessage(

          `�o. "${data.filename}" erfolgreich verarbeitet${processingInfo}\n` +

          `dY"? Gespeichert in: ${scopeInfo}` +

          (data.language !== 'unknown' ? `\ndYO? Sprache: ${data.language}` : '') +

          chunksInfo

        );



        if (onUploadComplete) {

          onUploadComplete([data]);

        }

      }



      setTimeout(() => {

        setSelectedFile(null);

        setUploadStatus('idle');

        setUploadMessage('');

      }, 3000);

    } catch (error) {

      setUploadStatus('error');

      const message = axios.isAxiosError(error)

        ? (error.response?.data as { detail?: string } | undefined)?.detail || error.message

        : String(error);

      setUploadMessage(`Upload fehlgeschlagen: ${message}`);

      console.error('Upload error:', error);

    } finally {

      setUploading(false);

    }



  };

  return (

    <Box sx={{ p: 2 }}>

      <Typography variant="h6" gutterBottom>

        Dokument hochladen

      </Typography>



      {/* File Input */}

      <Box sx={{ my: 2 }}>

        <input

          accept="*/*"

          style={{ display: 'none' }}

          id="file-upload-simple"

          type="file"

          onChange={handleFileSelect}

          disabled={uploading}

        />

        <label htmlFor="file-upload-simple">

          <Button

            variant="outlined"

            component="span"

            startIcon={<CloudUpload />}

            disabled={uploading}

            fullWidth

          >

            Datei auswählen

          </Button>

        </label>

      </Box>



      {/* Selected File */}

      {selectedFile && (

        <Box sx={{ my: 2 }}>

          <Typography variant="body2" color="text.secondary">

            Ausgewählte Datei: {selectedFile.name}

          </Typography>

          <Typography variant="caption" color="text.secondary">

            Größe: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB

          </Typography>

        </Box>

      )}



      {/* Upload Progress */}

      {uploading && (

        <Box sx={{ my: 2 }}>

          <LinearProgress />

        </Box>

      )}



      {/* Status Messages */}

      {uploadMessage && (

        <Alert

          severity={uploadStatus === 'success' ? 'success' : uploadStatus === 'error' ? 'error' : 'info'}

          sx={{ my: 2 }}

        >

          {uploadMessage}

        </Alert>

      )}



      {/* Action Buttons */}

      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>

        <Button

          variant="contained"

          color="primary"

          onClick={handleUpload}

          disabled={!selectedFile || uploading}

          startIcon={uploading ? <CircularProgress size={20} /> : <CloudUpload />}

        >

          {uploading ? 'Wird hochgeladen...' : 'Hochladen'}

        </Button>



        {onClose && (

          <Button

            variant="outlined"

            onClick={onClose}

            disabled={uploading}

          >

            Abbrechen

          </Button>

        )}

      </Box>

    </Box>

  );

};



export default SimpleUpload;