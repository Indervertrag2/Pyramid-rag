import React, { useState, useEffect, useRef } from 'react';
import { mcpClient } from '../services/MCPClient';
import {
  Box,
  IconButton,
  TextField,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Drawer,
  Avatar,
  Menu,
  MenuItem,
  Button,
  Divider,
  Chip,
  CircularProgress,
  Paper,
  Tooltip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Add as AddIcon,
  Send as SendIcon,
  Menu as MenuIcon,
  Logout as LogoutIcon,
  Dashboard as DashboardIcon,
  AttachFile as AttachFileIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  ContentCopy as CopyIcon,
  Folder as FolderIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Search as SearchIcon,
  CreateNewFolder as CreateFolderIcon,
  Business as CompanyIcon,
  Chat as ChatOnlyIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Public as PublicIcon,
  Group as GroupIcon,
  InsertDriveFile as InsertDriveFileIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  attachments?: File[];
  citations?: Array<{
    document_id: string;
    document_title: string;
    snippet: string;
    relevance_score: number;
  }>;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  folderId?: string;
  uploadedDocuments?: UploadedDocumentInfo[]; // Store uploaded documents for the session
  isTemporary?: boolean; // Indicates if this is a temporary chat (30 day expiry)
}

interface ChatFolder {
  id: string;
  name: string;
  color?: string;
  expanded: boolean;
}

interface UploadedDocumentInfo {
  id: string;
  documentId: string;
  title: string;
  filename: string;
  originalFilename: string;
  scope: 'GLOBAL' | 'CHAT';
  fileType?: string;
  mimeType?: string;
  content: string;
  contentLength?: number;
  metadata?: Record<string, any>;
  createdAt?: string;
  updatedAt?: string;
}

const ChatGPT: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [folders, setFolders] = useState<ChatFolder[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchEnabled, setSearchEnabled] = useState(true); // Toggle 1: Search
  const [saveToDatabase, setSaveToDatabase] = useState(true); // Toggle 2: Firmendatenbank vs Chat-Kontext
  const [documentVisibility, setDocumentVisibility] = useState<'department' | 'all'>('department'); // Toggle 3: Access (department or all)
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string[]>([]);
  const [documentPreview, setDocumentPreview] = useState<UploadedDocumentInfo | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const currentSession = sessions.find(session => session.id === currentSessionId) || null;
  const currentSessionDocuments = currentSession?.uploadedDocuments || [];

  const [editingTitleId, setEditingTitleId] = useState<string>('');
  const [newTitle, setNewTitle] = useState<string>('');
  const [editingFolderId, setEditingFolderId] = useState<string>('');
  const [newFolderName, setNewFolderName] = useState<string>('');

  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { darkMode, toggleDarkMode } = useTheme();

  const drawerWidth = 260;

  // Check if user is admin
  const isAdmin = user?.is_superuser || user?.roles?.includes('admin');

  // Cleanup function for uploads
  const cleanupUploads = React.useCallback(() => {
    if (abortControllers.current.length > 0) {
      console.log('Cleaning up active uploads...');
      abortControllers.current.forEach(controller => {
        controller.abort();
      });
      abortControllers.current = [];
      setUploading(false);
      isUploadingRef.current = false;
    }
  }, []);

  // Handle page unload/reload
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isUploadingRef.current) {
        // Try to abort uploads gracefully
        cleanupUploads();

        // Show warning to user (modern browsers may not show custom message)
        e.preventDefault();
        e.returnValue = 'Upload in Bearbeitung. Möchten Sie wirklich fortfahren?';
        return e.returnValue;
      }
    };

    // Add event listener
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Cleanup on unmount
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      cleanupUploads();
    };
  }, [cleanupUploads]);

  useEffect(() => {
    // Load sessions and folders from localStorage
    const savedSessions = localStorage.getItem('chatSessions');
    const savedFolders = localStorage.getItem('chatFolders');

    if (savedFolders) {
      setFolders(JSON.parse(savedFolders));
    } else {
      // Create default folder
      const defaultFolder = {
        id: 'default',
        name: 'Chats',
        expanded: true
      };
      setFolders([defaultFolder]);
      localStorage.setItem('chatFolders', JSON.stringify([defaultFolder]));
    }

    if (savedSessions) {
      const parsed = JSON.parse(savedSessions);
      setSessions(parsed);
      if (parsed.length > 0) {
        setCurrentSessionId(parsed[0].id);
        setMessages(parsed[0].messages || []);
      }
    } else {
      createNewSession();
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const createNewSession = (folderId: string = 'default', isTemporary: boolean = false) => {
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      title: isTemporary ? 'Temporärer Chat' : 'Neuer Chat',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      folderId,
      uploadedDocuments: [],
      isTemporary
    };

    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setMessages([]);

    // Save to localStorage
    const updatedSessions = [newSession, ...sessions];
    localStorage.setItem('chatSessions', JSON.stringify(updatedSessions));
  };

  const createNewFolder = () => {
    const newFolder: ChatFolder = {
      id: `folder-${Date.now()}`,
      name: 'Neuer Ordner',
      expanded: true
    };

    const updatedFolders = [...folders, newFolder];
    setFolders(updatedFolders);
    localStorage.setItem('chatFolders', JSON.stringify(updatedFolders));

    // Start editing immediately
    setEditingFolderId(newFolder.id);
    setNewFolderName(newFolder.name);
  };

  const toggleFolder = (folderId: string) => {
    const updatedFolders = folders.map(folder =>
      folder.id === folderId ? { ...folder, expanded: !folder.expanded } : folder
    );
    setFolders(updatedFolders);
    localStorage.setItem('chatFolders', JSON.stringify(updatedFolders));
  };

  const saveTitle = (sessionId: string) => {
    const updatedSessions = sessions.map(session =>
      session.id === sessionId ? { ...session, title: newTitle } : session
    );
    setSessions(updatedSessions);
    localStorage.setItem('chatSessions', JSON.stringify(updatedSessions));
    setEditingTitleId('');
  };

  const saveFolderName = (folderId: string) => {
    const updatedFolders = folders.map(folder =>
      folder.id === folderId ? { ...folder, name: newFolderName } : folder
    );
    setFolders(updatedFolders);
    localStorage.setItem('chatFolders', JSON.stringify(updatedFolders));
    setEditingFolderId('');
  };

  // Commented out - unused function
  // const moveSessionToFolder = (sessionId: string, folderId: string) => {
  //   const updatedSessions = sessions.map(session =>
  //     session.id === sessionId ? { ...session, folderId } : session
  //   );
  //   setSessions(updatedSessions);
  //   localStorage.setItem('chatSessions', JSON.stringify(updatedSessions));
  // };

  const deleteFolder = (folderId: string) => {
    if (folderId === 'default') return; // Cannot delete default folder

    // Move all sessions from this folder to default
    const updatedSessions = sessions.map(session =>
      session.folderId === folderId ? { ...session, folderId: 'default' } : session
    );
    setSessions(updatedSessions);
    localStorage.setItem('chatSessions', JSON.stringify(updatedSessions));

    // Delete the folder
    const updatedFolders = folders.filter(folder => folder.id !== folderId);
    setFolders(updatedFolders);
    localStorage.setItem('chatFolders', JSON.stringify(updatedFolders));
  };

  const selectSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setCurrentSessionId(sessionId);
      setMessages(session.messages || []);
    }
  };

  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId);
    setSessions(updatedSessions);
    localStorage.setItem('chatSessions', JSON.stringify(updatedSessions));

    if (currentSessionId === sessionId) {
      if (updatedSessions.length > 0) {
        selectSession(updatedSessions[0].id);
      } else {
        createNewSession();
      }
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() && uploadedFiles.length === 0) return;
    if (loading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
      attachments: uploadedFiles.length > 0 ? [...uploadedFiles] : undefined
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputMessage('');
    setLoading(true);

    // Update session title if it's the first message
    if (messages.length === 0) {
      const currentSession = sessions.find(s => s.id === currentSessionId);
      if (currentSession) {
        currentSession.title = inputMessage.slice(0, 30) + (inputMessage.length > 30 ? '...' : '');
        currentSession.updatedAt = new Date();
        setSessions([...sessions]);
        localStorage.setItem('chatSessions', JSON.stringify(sessions));
      }
    }

    // Handle file uploads if present and get uploaded document data
    let newUploadedDocuments: any[] = [];
    if (uploadedFiles.length > 0) {
      newUploadedDocuments = await handleFileUpload();
    }

    // Get all documents for this session (previous + new)
    const currentSession = sessions.find(s => s.id === currentSessionId);
    const sessionDocuments = [
      ...(currentSession?.uploadedDocuments || []),
      ...newUploadedDocuments
    ];

    // Update session with new documents if any
    if (newUploadedDocuments.length > 0 && currentSession) {
      currentSession.uploadedDocuments = sessionDocuments;
      localStorage.setItem('chatSessions', JSON.stringify(sessions));
    }

    // Prepare chat content - include file content if available
    let chatContent = userMessage.content;
    if (sessionDocuments.length > 0) {
      const fileContents = sessionDocuments.map(doc =>
        `\n\n--- Datei: ${doc.title} ---\n${doc.content || 'Inhalt nicht verfügbar'}\n--- Ende Datei ---`
      ).join('');
      chatContent = `${userMessage.content}\n\nVerfügbare Dateien:${fileContents}`;
    }

    try {
      const token = localStorage.getItem('access_token');
      // Update MCP client token
      if (token) {
        mcpClient.updateToken(token);
      }

      // Create assistant message placeholder for streaming
      const assistantMessage: Message = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        citations: []
      };

      let streamContent = '';
      const updatedMessages = [...newMessages, assistantMessage];
      setMessages(updatedMessages);

      // Use MCP client to stream message
      await mcpClient.streamMessage(chatContent, {
        tools: searchEnabled ? ['chat', 'hybrid_search'] : ['chat'],
        rag_enabled: searchEnabled,
        session_id: currentSessionId,
        department: user?.primary_department || 'UNKNOWN',
        uploaded_documents: sessionDocuments.map(doc => ({
          id: doc.id,
          title: doc.title,
          content: doc.content
        })),
        onChunk: (chunk: string) => {
          streamContent += chunk;
          // Update the assistant message with accumulated content
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...lastMessage, content: streamContent }
              ];
            }
            return prev;
          });
        },
        onComplete: () => {
          // Streaming complete
          console.log('Streaming complete');
        },
        onError: (error: string) => {
          console.error('Streaming error:', error);
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...lastMessage, content: `Error: ${error}` }
              ];
            }
            return prev;
          });
        }
      });

      // Update session after streaming
      const finalSession = sessions.find(s => s.id === currentSessionId);
      if (finalSession) {
        finalSession.messages = messages; // Use current messages state
        finalSession.updatedAt = new Date();
        finalSession.uploadedDocuments = sessionDocuments;
        setSessions([...sessions]);
        localStorage.setItem('chatSessions', JSON.stringify(sessions));
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: `msg-${Date.now()}-error`,
        role: 'system',
        content: 'Fehler bei der Verarbeitung Ihrer Nachricht.',
        timestamp: new Date()
      };
      setMessages([...newMessages, errorMessage]);
    } finally {
      setLoading(false);
      setUploadedFiles([]);
      setUploadSuccess([]);
    }
  };

  // Store abort controllers for cleanup
  const abortControllers = React.useRef<AbortController[]>([]);
  const isUploadingRef = React.useRef<boolean>(false);

  const handleFileUpload = async (): Promise<any[]> => {
    if (uploadedFiles.length === 0) return [];

    // Only upload if saveToDatabase is true
    if (!saveToDatabase) {
      console.log('📎 Files attached for current message only (not saving to database)');
      return uploadedFiles.map(file => ({
        id: `temp-${Date.now()}-${file.name}`,
        filename: file.name,
        content: file,
        temporary: true
      }));
    }

    setUploading(true);
    isUploadingRef.current = true;
    const uploadedDocuments: any[] = [];

    // Clear previous abort controllers
    abortControllers.current = [];

    for (const file of uploadedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('scope', saveToDatabase ? 'GLOBAL' : 'CHAT');
      formData.append('visibility', documentVisibility); // "all" or "department"
      if (!saveToDatabase && currentSessionId) {
        formData.append('session_id', currentSessionId);
      }

      // Debug logging
      console.log('💾 Saving file to database:', {
        filename: file.name,
        size: file.size,
        type: file.type,
        scope: saveToDatabase ? 'GLOBAL' : 'CHAT',
        saveToDatabase: true,
        sessionId: currentSessionId
      });

      try {
        const token = localStorage.getItem('access_token');

        // Create abort controller for this upload
        const abortController = new AbortController();
        abortControllers.current.push(abortController);

        // 🚀 Use new unified upload API (2025)
        const response = await fetch('http://localhost:18000/api/v1/documents/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData,
          signal: abortController.signal
        });

        if (response.ok) {
          const documentData = await response.json();

          if (documentData.duplicate) {
            // Handle duplicate detection
            setUploadSuccess(prev => [...prev, `📄 ${file.name} bereits vorhanden (übersprungen)`]);
          } else {
            uploadedDocuments.push(documentData);
            console.log('✅ File processed successfully:', documentData);

            // Enhanced success message with processing details
            const processingTime = documentData.processing_time ? ` (${documentData.processing_time.toFixed(1)}s)` : '';
            const scopeLabel = documentData.scope === 'GLOBAL' ? '🏢' : '💬';
            const chunksInfo = documentData.chunks_created > 0 ? `, ${documentData.chunks_created} Chunks` : '';

            setUploadSuccess(prev => [...prev, `${scopeLabel} ${file.name}${processingTime}${chunksInfo}`]);
          }
        } else {
          const errorText = await response.text();
          console.error('Upload failed:', {
            status: response.status,
            statusText: response.statusText,
            error: errorText,
            file: file.name,
            department: 'Management'
          });

          // Try to parse error for more details
          try {
            const errorJson = JSON.parse(errorText);
            console.error('Error details:', errorJson);

            // Show specific error message
            const errorMsg = errorJson.detail?.[0]?.msg || errorJson.detail || 'Unbekannter Fehler';
            setUploadSuccess(prev => [...prev, `Upload von ${file.name} fehlgeschlagen: ${errorMsg}`]);
          } catch {
            setUploadSuccess(prev => [...prev, `Upload von ${file.name} fehlgeschlagen: ${response.status}`]);
          }
        }
      } catch (error: any) {
        // Check if upload was aborted
        if (error.name === 'AbortError') {
          console.log('Upload aborted for file:', file.name);
          setUploadSuccess(prev => [...prev, `Upload von ${file.name} abgebrochen`]);
        } else {
          console.error('Upload error:', error);
          setUploadSuccess(prev => [...prev, `Upload von ${file.name} fehlgeschlagen: ${error.message}`]);
        }
      }
    }

    // Clear abort controllers after upload completes
    abortControllers.current = [];
    setUploading(false);
    isUploadingRef.current = false;
    return uploadedDocuments;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const openDocumentPreview = (doc: UploadedDocumentInfo) => {
    setDocumentPreview(doc);
    setPreviewOpen(true);
  };

  const closeDocumentPreview = () => {
    setPreviewOpen(false);
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: darkMode ? '#1e1e1e' : '#fafafa' }}>
      {/* Sidebar */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={sidebarOpen}
        sx={{
          width: sidebarOpen ? drawerWidth : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: darkMode ? '#1a1a1a' : '#ffffff',
            borderRight: darkMode ? '1px solid #2d2d2d' : '1px solid #e5e5e5'
          }
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 400, fontSize: '1.1rem', color: 'text.secondary' }}>
            Pyramid RAG
          </Typography>
        </Box>

        <Box sx={{ px: 2, pb: 2 }}>
          <Button
            fullWidth
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => createNewSession('default', false)}
            sx={{
              justifyContent: 'flex-start',
              textTransform: 'none',
              bgcolor: '#003d7a',
              color: 'white',
              borderRadius: '12px',
              py: 1,
              mb: 1,
              fontSize: '0.9rem',
              '&:hover': {
                bgcolor: '#002855'
              }
            }}
          >
            Neuer Chat
          </Button>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => createNewSession('default', true)}
            sx={{
              justifyContent: 'flex-start',
              textTransform: 'none',
              borderColor: '#d9027d',
              color: '#d9027d',
              borderRadius: '12px',
              py: 0.75,
              mb: 1,
              fontSize: '0.85rem',
              '&:hover': {
                borderColor: '#f57c00',
                bgcolor: 'rgba(255, 152, 0, 0.08)'
              }
            }}
          >
            Temporärer Chat (30 Tage)
          </Button>
          <Button
            fullWidth
            variant="text"
            startIcon={<CreateFolderIcon />}
            onClick={createNewFolder}
            sx={{
              justifyContent: 'flex-start',
              textTransform: 'none',
              color: 'text.secondary',
              borderRadius: '12px',
              py: 0.5,
              fontSize: '0.9rem',
              '&:hover': {
                bgcolor: darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'
              }
            }}
          >
            Neuer Ordner
          </Button>
        </Box>

        <Divider sx={{ mx: 1 }} />

        <List sx={{ flexGrow: 1, overflow: 'auto', px: 1, py: 1 }}>
          {folders.map((folder) => (
            <Box key={folder.id} sx={{ mb: 1 }}>
              <ListItem disablePadding>
                <ListItemButton
                  onClick={() => toggleFolder(folder.id)}
                  sx={{
                    borderRadius: '8px',
                    py: 0.5,
                    minHeight: 32,
                    '&:hover': {
                      bgcolor: darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'
                    }
                  }}
                >
                  <IconButton size="small" sx={{ p: 0, mr: 1 }}>
                    {folder.expanded ? <ExpandMoreIcon fontSize="small" /> : <ExpandLessIcon fontSize="small" />}
                  </IconButton>
                  <FolderIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />

                  {editingFolderId === folder.id ? (
                    <TextField
                      size="small"
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      onBlur={() => saveFolderName(folder.id)}
                      onKeyPress={(e) => e.key === 'Enter' && saveFolderName(folder.id)}
                      sx={{ fontSize: '0.9rem' }}
                      autoFocus
                    />
                  ) : (
                    <Typography
                      variant="body2"
                      sx={{
                        flexGrow: 1,
                        fontSize: '0.9rem',
                        color: 'text.primary'
                      }}
                    >
                      {folder.name}
                    </Typography>
                  )}

                  {folder.id !== 'default' && (
                    <>
                      {/* Edit Folder Icon */}
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingFolderId(folder.id);
                          setNewFolderName(folder.name);
                        }}
                        sx={{
                          ml: 0.5,
                          opacity: 0,
                          transition: 'opacity 0.2s',
                          '&:hover': { opacity: 1 }
                        }}
                      >
                        <EditIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                      {/* Delete Folder Icon */}
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFolder(folder.id);
                        }}
                        sx={{
                          ml: 0.5,
                          opacity: 0,
                          transition: 'opacity 0.2s',
                          '&:hover': { opacity: 1 }
                        }}
                      >
                        <DeleteIcon sx={{ fontSize: 14 }} />
                      </IconButton>
                    </>
                  )}
                </ListItemButton>
              </ListItem>

              {folder.expanded && (
                <List sx={{ pl: 3 }}>
                  {sessions
                    .filter(session => (session.folderId || 'default') === folder.id)
                    .map((session) => (
                      <ListItem
                        key={session.id}
                        disablePadding
                        sx={{ mb: 0.5 }}
                      >
                        <ListItemButton
                          selected={currentSessionId === session.id}
                          onClick={() => selectSession(session.id)}
                          sx={{
                            borderRadius: '8px',
                            py: 0.5,
                            minHeight: 32,
                            pl: 1,
                            '&.Mui-selected': {
                              bgcolor: darkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
                              '&:hover': {
                                bgcolor: darkMode ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)'
                              }
                            },
                            '&:hover': {
                              bgcolor: darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'
                            }
                          }}
                        >
                          {editingTitleId === session.id ? (
                            <TextField
                              size="small"
                              value={newTitle}
                              onChange={(e) => setNewTitle(e.target.value)}
                              onBlur={() => saveTitle(session.id)}
                              onKeyPress={(e) => e.key === 'Enter' && saveTitle(session.id)}
                              sx={{ fontSize: '0.85rem' }}
                              autoFocus
                              fullWidth
                            />
                          ) : (
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  <Typography
                                    variant="body2"
                                    noWrap
                                    sx={{
                                      fontSize: '0.85rem',
                                      color: 'text.primary'
                                    }}
                                  >
                                    {session.title}
                                  </Typography>
                                  {session.isTemporary && (
                                    <Chip
                                      label="Temp"
                                      size="small"
                                      sx={{
                                        height: 16,
                                        fontSize: '0.65rem',
                                        bgcolor: darkMode ? 'rgba(245, 124, 0, 0.2)' : 'rgba(245, 124, 0, 0.1)',
                                        color: '#f57c00'
                                      }}
                                    />
                                  )}
                                </Box>
                              }
                            />
                          )}
                          {/* Edit Icon */}
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingTitleId(session.id);
                              setNewTitle(session.title);
                            }}
                            sx={{
                              ml: 0.5,
                              opacity: currentSessionId === session.id ? 1 : 0,
                              transition: 'opacity 0.2s',
                              '&:hover': { opacity: 1 }
                            }}
                          >
                            <EditIcon sx={{ fontSize: 14 }} />
                          </IconButton>
                          {/* Delete Icon */}
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSession(session.id);
                            }}
                            sx={{
                              ml: 0.5,
                              opacity: currentSessionId === session.id ? 1 : 0,
                              transition: 'opacity 0.2s',
                              '&:hover': { opacity: 1 }
                            }}
                          >
                            <DeleteIcon sx={{ fontSize: 14 }} />
                          </IconButton>
                        </ListItemButton>
                      </ListItem>
                    ))}
                </List>
              )}
            </Box>
          ))}
        </List>

        <Divider sx={{ mx: 1 }} />

        <Box sx={{ p: 1.5 }}>
          {isAdmin && (
            <Button
              fullWidth
              variant="text"
              startIcon={<DashboardIcon />}
              onClick={() => navigate('/dashboard')}
              sx={{
                mb: 0.5,
                textTransform: 'none',
                justifyContent: 'flex-start',
                color: 'text.secondary',
                fontSize: '0.85rem',
                py: 0.5,
                borderRadius: '8px',
                '&:hover': {
                  bgcolor: darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'
                }
              }}
            >
              Admin Dashboard
            </Button>
          )}

          <Button
            fullWidth
            variant="text"
            startIcon={<LogoutIcon />}
            onClick={handleLogout}
            sx={{
              textTransform: 'none',
              justifyContent: 'flex-start',
              color: 'text.secondary',
              fontSize: '0.85rem',
              py: 0.5,
              borderRadius: '8px',
              '&:hover': {
                bgcolor: darkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)'
              }
            }}
          >
            Abmelden
          </Button>

        </Box>
      </Drawer>

      {/* Main Chat Area */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{
          borderBottom: darkMode ? '1px solid #2d2d2d' : '1px solid #e5e5e5',
          bgcolor: darkMode ? '#1e1e1e' : '#ffffff',
          px: 3,
          py: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 2
        }}>
          <IconButton
            onClick={() => setSidebarOpen(!sidebarOpen)}
            size="small"
            sx={{ color: 'text.secondary' }}
          >
            <MenuIcon fontSize="small" />
          </IconButton>

          <Typography variant="h6" sx={{ flexGrow: 1, fontSize: '1rem', fontWeight: 400, color: 'text.primary' }}>
            {sessions.find(s => s.id === currentSessionId)?.title || 'Chat'}
          </Typography>

          {/* Dark Mode Toggle */}
          <IconButton
            onClick={toggleDarkMode}
            size="small"
            sx={{ color: 'text.secondary' }}
          >
            {darkMode ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
          </IconButton>


          <Avatar
            sx={{
              bgcolor: 'text.secondary',
              cursor: 'pointer',
              width: 32,
              height: 32,
              fontSize: '0.85rem',
              borderRadius: '50%'
            }}
            onClick={(e) => setAnchorEl(e.currentTarget)}
          >
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </Avatar>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            PaperProps={{
              sx: {
                mt: 1,
                minWidth: 180,
                bgcolor: darkMode ? '#2a2a2a' : '#ffffff',
                border: darkMode ? '1px solid #3d3d3d' : '1px solid #e5e5e5'
              }
            }}
          >
            <MenuItem disabled sx={{ fontSize: '0.85rem' }}>
              {user?.email}
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout} sx={{ fontSize: '0.85rem' }}>
              <LogoutIcon sx={{ mr: 1, fontSize: 16 }} /> Abmelden
            </MenuItem>
          </Menu>
        </Box>

        {/* Messages Area */}
        <Box sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }}>
          <Box sx={{ width: '100%', maxWidth: 800 }}>
            {messages.length === 0 ? (
              <Box sx={{
                textAlign: 'center',
                py: 10
              }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 300 }}>
                  Wie kann ich Ihnen helfen?
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Stellen Sie Fragen, laden Sie Dokumente hoch oder erkunden Sie die Plattform
                </Typography>
              </Box>
            ) : (
              <>
                {messages.map((message) => (
                  <Box
                    key={message.id}
                    sx={{
                      mb: 3,
                      display: 'flex',
                      justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start'
                    }}
                  >
                    {message.role !== 'user' && (
                      <Avatar sx={{
                        bgcolor: '#10a37f',
                        mr: 2,
                        width: 32,
                        height: 32,
                        borderRadius: '50%'
                      }}>
                        AI
                      </Avatar>
                    )}

                    <Paper
                      sx={{
                        p: 2,
                        maxWidth: '70%',
                        bgcolor: message.role === 'user'
                          ? (darkMode ? '#4a5568' : '#e3f2fd')
                          : (darkMode ? '#2d3748' : 'white'),
                        borderRadius: '16px'
                      }}
                    >
                      <Typography sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {message.content}
                      </Typography>

                      {message.attachments && message.attachments.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          {message.attachments.map((file, idx) => (
                            <Chip
                              key={idx}
                              label={file.name}
                              size="small"
                              icon={<AttachFileIcon />}
                              sx={{ mr: 1, mb: 1 }}
                            />
                          ))}
                        </Box>
                      )}

                      {message.role === 'assistant' && (
                        <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                          <IconButton size="small" onClick={() => handleCopy(message.content)}>
                            <CopyIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      )}
                    </Paper>

                    {message.role === 'user' && (
                      <Avatar sx={{
                        bgcolor: 'primary.main',
                        ml: 2,
                        width: 32,
                        height: 32,
                        borderRadius: '50%'
                      }}>
                        {user?.username?.[0]?.toUpperCase() || 'U'}
                      </Avatar>
                    )}
                  </Box>
                ))}

                {loading && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                    <Avatar sx={{ bgcolor: '#10a37f', width: 32, height: 32 }}>
                      AI
                    </Avatar>
                    <CircularProgress size={20} />
                  </Box>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </Box>
        </Box>

        {/* Input Area */}
        <Box sx={{
          p: 2,
          borderTop: darkMode ? '1px solid #333' : '1px solid #e0e0e0',
          bgcolor: darkMode ? '#1e1e1e' : 'white'
        }}>
          <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
            {uploadedFiles.length > 0 && (
              <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {uploadedFiles.map((file, idx) => (
                  <Chip
                    key={idx}
                    label={file.name}
                    onDelete={() => setUploadedFiles(files => files.filter((_, i) => i !== idx))}
                    icon={<AttachFileIcon />}
                    color="primary"
                  />
                ))}
              </Box>
            )}

            {/* Toggles Row - Separate line above input */}
            <Box sx={{
              mb: 2,
              display: 'flex',
              gap: 2,
              justifyContent: 'flex-start',
              flexWrap: 'wrap'
            }}>
              {/* Search Toggle */}
              <Chip
                icon={<SearchIcon />}
                label="Suche"
                onClick={() => setSearchEnabled(!searchEnabled)}
                variant={searchEnabled ? "filled" : "outlined"}
                size="medium"
                sx={{
                  minWidth: '160px',
                  height: 38,
                  '& .MuiChip-icon': {
                    fontSize: '1.2rem',
                    color: searchEnabled ? 'white' : (darkMode ? 'white' : 'inherit')
                  },
                  '& .MuiChip-label': { px: 1.5, fontSize: '0.95rem', fontWeight: 500 },
                  bgcolor: searchEnabled ? '#003d7a' : 'transparent',
                  color: searchEnabled ? 'white' : (darkMode ? 'white' : 'text.primary'),
                  borderColor: searchEnabled ? '#003d7a' : (darkMode ? 'rgba(255,255,255,0.3)' : 'divider'),
                  borderWidth: 2,
                  '&:hover': {
                    bgcolor: searchEnabled ? '#002855' : 'action.hover',
                    borderColor: '#003d7a'
                  },
                  transition: 'all 0.2s ease'
                }}
              />

              {/* Save to Database Toggle (only visible when files attached) */}
              {uploadedFiles.length > 0 && (
                <>
                  <Chip
                    icon={saveToDatabase ? <CompanyIcon /> : <ChatOnlyIcon />}
                    label={saveToDatabase ? "Firmendatenbank" : "Chat-Kontext"}
                    onClick={() => setSaveToDatabase(!saveToDatabase)}
                    variant={saveToDatabase ? "filled" : "outlined"}
                    size="medium"
                    sx={{
                      minWidth: '160px',
                      height: 38,
                      '& .MuiChip-icon': {
                        fontSize: '1.2rem',
                        color: saveToDatabase ? 'white' : (darkMode ? 'white' : 'inherit')
                      },
                      '& .MuiChip-label': { px: 1.5, fontSize: '0.95rem', fontWeight: 500 },
                      bgcolor: saveToDatabase ? '#003d7a' : 'transparent',
                      color: saveToDatabase ? 'white' : (darkMode ? 'white' : 'text.primary'),
                      borderColor: saveToDatabase ? '#003d7a' : (darkMode ? 'rgba(255,255,255,0.3)' : 'divider'),
                      borderWidth: 2,
                      '&:hover': {
                        bgcolor: saveToDatabase ? '#002855' : 'action.hover',
                        borderColor: '#003d7a'
                      },
                      transition: 'all 0.2s ease'
                    }}
                  />

                  {/* Visibility Toggle (only visible when saving to database) */}
                  {saveToDatabase && (
                    <Chip
                      icon={documentVisibility === 'all' ? <PublicIcon /> : <GroupIcon />}
                      label={documentVisibility === 'all' ? 'Alle' : 'Nur Abteilung'}
                      onClick={() => setDocumentVisibility(documentVisibility === 'all' ? 'department' : 'all')}
                      variant={documentVisibility === 'all' ? "filled" : "outlined"}
                      size="medium"
                      sx={{
                        minWidth: '160px',
                        height: 38,
                        '& .MuiChip-icon': {
                          fontSize: '1.2rem',
                          color: documentVisibility === 'all' ? 'white' : (darkMode ? 'white' : 'inherit')
                        },
                        '& .MuiChip-label': { px: 1.5, fontSize: '0.95rem', fontWeight: 500 },
                        bgcolor: documentVisibility === 'all' ? '#003d7a' : 'transparent',
                        color: documentVisibility === 'all' ? 'white' : (darkMode ? 'white' : 'text.primary'),
                        borderColor: documentVisibility === 'all' ? '#003d7a' : (darkMode ? 'rgba(255,255,255,0.3)' : 'divider'),
                        borderWidth: 2,
                        '&:hover': {
                          bgcolor: documentVisibility === 'all' ? '#002855' : 'action.hover',
                          borderColor: '#003d7a'
                        },
                        transition: 'all 0.2s ease'
                      }}
                    />
                  )}

                </>
              )}

            </Box>

            {/* Input Field Row */}
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', width: '100%' }}>
              <input
                type="file"
                multiple
                ref={fileInputRef}
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                accept=".txt,.pdf,.docx,.xlsx,.pptx,.md,.json,.csv,.xml,.html"
              />


              {/* Attachment button */}
              <Tooltip title="Dateien anhängen">
                <IconButton
                  onClick={() => fileInputRef.current?.click()}
                  sx={{
                    color: darkMode ? 'grey.400' : 'grey.600',
                    '&:hover': { color: '#003d7a' },
                    alignSelf: 'center',
                    mb: 0.5
                  }}
                >
                  <AttachFileIcon />
                </IconButton>
              </Tooltip>

              {/* Input field - takes remaining space */}
              <TextField
                fullWidth
                multiline
                maxRows={4}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={uploadedFiles.length > 0 ? "Beschreibe deine Dateien oder stelle eine Frage..." : "Nachricht eingeben..."}
                disabled={loading}
                sx={{
                  flexGrow: 1,
                  '& .MuiOutlinedInput-root': {
                    borderRadius: '24px',
                    bgcolor: darkMode ? '#2a2a2a' : '#f5f5f5',
                    pr: 0.5,
                    '&:hover fieldset': {
                      borderColor: '#003d7a'
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#003d7a',
                      borderWidth: 2
                    }
                  }
                }}
                InputProps={{
                  endAdornment: (
                    <IconButton
                      onClick={sendMessage}
                      disabled={loading || (!inputMessage.trim() && uploadedFiles.length === 0)}
                      sx={{
                        bgcolor: loading ? 'transparent' : '#003d7a',
                        color: loading ? 'grey.500' : 'white',
                        borderRadius: '50%',
                        mr: 0.5,
                        '&:hover': { bgcolor: loading ? 'transparent' : '#002855' },
                        '&:disabled': {
                          bgcolor: 'action.disabledBackground',
                          color: 'action.disabled'
                        }
                      }}
                    >
                      {loading ? <CircularProgress size={24} /> : <SendIcon />}
                    </IconButton>
                  )
                }}
              />
            </Box>

            {uploading && (
              <Box sx={{ mt: 1 }}>
                <LinearProgress />
                <Typography variant="caption">Dateien werden hochgeladen...</Typography>
              </Box>
            )}

            {/* Upload Success/Error Messages */}
            {uploadSuccess.length > 0 && (
              <Box sx={{ mt: 1 }}>
                {uploadSuccess.map((message, idx) => (
                  <Typography
                    key={idx}
                    variant="caption"
                    sx={{
                      display: 'block',
                      color: message.includes('fehlgeschlagen') ? 'error.main' : 'success.main',
                      fontSize: '0.75rem'
                    }}
                  >
                    ✓ {message}
                  </Typography>
                ))}
              </Box>
            )}

            {/* Show documents available in session */}
            {sessions.find(s => s.id === currentSessionId)?.uploadedDocuments && sessions.find(s => s.id === currentSessionId)?.uploadedDocuments && sessions.find(s => s.id === currentSessionId)!.uploadedDocuments!.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                  Verfügbare Dateien in dieser Session: {
                    sessions.find(s => s.id === currentSessionId)?.uploadedDocuments?.map(d => d.title)?.join(', ') || ''
                  }
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatGPT;