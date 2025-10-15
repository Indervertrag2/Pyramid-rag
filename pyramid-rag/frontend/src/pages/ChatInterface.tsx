import React, { useState, useEffect, useRef } from 'react';

import Sidebar from '../components/sidebar/Sidebar';
import ChatHeader from '../components/chat/ChatHeader';
import MessageList from '../components/chat/MessageList';
import ChatInput from '../components/chat/ChatInput';
import type { ChatFolder, ChatSession, DocumentPreviewState, Message, UploadOutcome, ConversationDocument, UploadedDocumentInfo } from '../types';

import { mcpClient } from '../services/MCPClient';
import type { MCPMessage } from '../services/MCPClient';
import { chatApi, type ApiChatMessage } from '../services/chatApi';


import { normalizeUploadedDocument, buildUploadAcknowledgement, normalizeConversationDocuments } from '../utils/chatDocuments';


import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  TextField,
  Chip
} from '@mui/material';


import { useNavigate } from 'react-router-dom';


import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';

import { useAuth } from '../contexts/AuthContext';


import { useTheme } from '../contexts/ThemeContext';





const CONTEXT_WINDOW_SIZE = 5;
const AUTO_SCROLL_THRESHOLD = 120;

const ChatGPT: React.FC = () => {



  const [sessions, setSessions] = useState<ChatSession[]>([]);


  const [folders, setFolders] = useState<ChatFolder[]>([]);


  const [currentSessionId, setCurrentSessionId] = useState<string>('');


  const [messages, setMessages] = useState<Message[]>([]);


  const [lastContextDocuments, setLastContextDocuments] = useState<ConversationDocument[]>([]);


  const [inputMessage, setInputMessage] = useState('');


  const [loading, setLoading] = useState(false);


  const [searchEnabled, setSearchEnabled] = useState(true); // Toggle 1: Search


  const [saveToDatabase, setSaveToDatabase] = useState(true); // Toggle 2: Firmendatenbank vs Chat-Kontext


  const [documentVisibility, setDocumentVisibility] = useState<'department' | 'all'>('department'); // Toggle 3: Access (department or all)


  const [sidebarOpen, setSidebarOpen] = useState(true);




  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);


  const [uploading, setUploading] = useState(false);


  const [uploadSuccess, setUploadSuccess] = useState<string[]>([]);


  const [documentPreview, setDocumentPreview] = useState<DocumentPreviewState | null>(null);


  const [previewOpen, setPreviewOpen] = useState(false);


  const [previewLoading, setPreviewLoading] = useState(false);


  const [previewError, setPreviewError] = useState<string | null>(null);





  const currentSession = sessions.find(session => session.id === currentSessionId) || null;


  const currentSessionDocuments: UploadedDocumentInfo[] = currentSession?.uploadedDocuments || [];





  const [editingTitleId, setEditingTitleId] = useState<string>('');


  const [newTitle, setNewTitle] = useState<string>('');


  const [editingFolderId, setEditingFolderId] = useState<string>('');


  const [newFolderName, setNewFolderName] = useState<string>('');

  // Publish dialog state
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [publishTitle, setPublishTitle] = useState('');
  const [publishDescription, setPublishDescription] = useState('');
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishSuccess, setPublishSuccess] = useState(false);





  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const autoScrollRef = useRef(true);
  const activeHistoryRequestRef = useRef<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);


  const navigate = useNavigate();


  const { user, logout } = useAuth();


  const { darkMode, toggleDarkMode } = useTheme();





  const drawerWidth = 260;





  // Check if user is admin


  const isAdmin = Boolean(user?.is_superuser || user?.roles?.includes('admin'));





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

  // Load sessions from database on mount
  useEffect(() => {
    const loadSessionsFromDatabase = async () => {
      try {
        const apiSessions = await chatApi.getSessions();
        const loadedSessions: ChatSession[] = apiSessions.map(s => ({
          id: s.id,
          title: s.title,
          folderId: s.folder_path || 'default',
          messages: [], // Messages loaded on demand when session is selected
          createdAt: new Date(s.created_at),
          updatedAt: new Date(s.updated_at),
          uploadedDocuments: [],
          isTemporary: s.chat_type === 'TEMPORARY'
        }));
        setSessions(loadedSessions);

        // Load most recent session if exists
        if (loadedSessions.length > 0 && !currentSessionId) {
          const mostRecent = loadedSessions[0];
          setCurrentSessionId(mostRecent.id);

          // Load messages for most recent session
          try {
            const apiMessages = await chatApi.getSessionMessages(mostRecent.id);
            const loadedMessages: Message[] = apiMessages.map(m => ({
              id: m.id,
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: new Date(m.created_at),
              citations: normalizeConversationDocuments(m.meta_data?.retrieved_documents || [])
            }));
            setMessages(loadedMessages);
          } catch (error) {
            console.error('Failed to load messages:', error);
          }
        }
      } catch (error) {
        console.error('Failed to load sessions from database:', error);
        // Create initial session if loading fails
        createNewSession('default', false);
      }
    };

    loadSessionsFromDatabase();
  }, []);

  useEffect(() => {
    if (!autoScrollRef.current) {
      return;
    }
    const behavior: ScrollBehavior = messages.length > 20 ? 'auto' : 'smooth';
    scrollToBottom(behavior);
  }, [messages]);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior, block: 'end' });
    }
  };

  useEffect(() => {
    return () => {
      cleanupUploads();
    };
  }, [cleanupUploads]);

  const handleMessagesScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const distanceToBottom = container.scrollHeight - (container.scrollTop + container.clientHeight);
    autoScrollRef.current = distanceToBottom <= AUTO_SCROLL_THRESHOLD;
  };

  const createNewSession = async (folderId: string = 'default', isTemporary: boolean = false): Promise<ChatSession> => {
    try {
      // Create session in database
      const apiSession = await chatApi.createSession({
        title: isTemporary ? 'Temporarer Chat' : 'Neuer Chat',
        folder_path: folderId === 'default' ? null : folderId,
        is_temporary: isTemporary
      });

      // Convert to frontend format
      const newSession: ChatSession = {
        id: apiSession.id,
        title: apiSession.title,
        folderId: apiSession.folder_path || 'default',
        messages: [],
        createdAt: new Date(apiSession.created_at),
        updatedAt: new Date(apiSession.updated_at),
        uploadedDocuments: [],
        isTemporary: apiSession.chat_type === 'TEMPORARY'
      };

      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
      setLastContextDocuments([]);

      return newSession;
    } catch (error) {
      console.error('Failed to create session in database:', error);
      // Fallback to local-only session
      const newSession: ChatSession = {
        id: `session-${Date.now()}`,
        title: isTemporary ? 'Temporarer Chat' : 'Neuer Chat',
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
      setLastContextDocuments([]);
      return newSession;
    }
  };





  const createNewFolder = () => {


    const newFolder: ChatFolder = {


      id: `folder-${Date.now()}`,


      name: 'Neuer Ordner',


      expanded: true


    };





    const updatedFolders = [...folders, newFolder];


    setFolders(updatedFolders);







    // Start editing immediately


    setEditingFolderId(newFolder.id);


    setNewFolderName(newFolder.name);


  };





  const toggleFolder = (folderId: string) => {


    const updatedFolders = folders.map(folder =>


      folder.id === folderId ? { ...folder, expanded: !folder.expanded } : folder


    );


    setFolders(updatedFolders);




  };





  const moveSessionToFolder = async (sessionId: string, folderId: string | null) => {
    try {
      // Update in database
      await chatApi.updateSession(sessionId, {
        folder_path: folderId === 'default' || folderId === null ? null : folderId
      });

      // Update local state
      const updatedSessions = sessions.map(session =>
        session.id === sessionId
          ? { ...session, folderId: folderId || 'default' }
          : session
      );
      setSessions(updatedSessions);
    } catch (error) {
      console.error('Failed to update session folder:', error);
    }
  };




  const saveTitle = (sessionId: string) => {


    const updatedSessions = sessions.map(session =>


      session.id === sessionId ? { ...session, title: newTitle } : session


    );


    setSessions(updatedSessions);




    setEditingTitleId('');


  };





  const saveFolderName = (folderId: string) => {


    const updatedFolders = folders.map(folder =>


      folder.id === folderId ? { ...folder, name: newFolderName } : folder


    );


    setFolders(updatedFolders);




    setEditingFolderId('');


  };





  // Commented out - unused function


  // const moveSessionToFolder = (sessionId: string, folderId: string) => {


  //   const updatedSessions = sessions.map(session =>


  //     session.id === sessionId ? { ...session, folderId } : session


  //   );


  //   setSessions(updatedSessions);




  // };





  const deleteFolder = (folderId: string) => {


    if (folderId === 'default') return; // Cannot delete default folder





    // Move all sessions from this folder to default


    const updatedSessions = sessions.map(session =>


      session.folderId === folderId ? { ...session, folderId: 'default' } : session


    );


    setSessions(updatedSessions);







    // Delete the folder


    const updatedFolders = folders.filter(folder => folder.id !== folderId);


    setFolders(updatedFolders);




  };






const selectSession = async (sessionId: string, fallbackSession?: ChatSession) => {
  autoScrollRef.current = true;
  setCurrentSessionId(sessionId);

  const sessionFromState = sessions.find(s => s.id === sessionId);
  const session = sessionFromState ?? fallbackSession ?? null;

  if (session?.messages && session.messages.length > 0) {
    setMessages(session.messages);
    const localAssistant = [...session.messages].reverse().find(msg => msg.role === 'assistant' && Array.isArray(msg.citations) && msg.citations.length > 0);
    if (localAssistant?.citations) {
      setLastContextDocuments(localAssistant.citations);
    }
  } else {
    setMessages([]);
  }

  activeHistoryRequestRef.current = sessionId;

  try {
    const apiMessages: ApiChatMessage[] = await chatApi.getSessionMessages(sessionId);
    if (activeHistoryRequestRef.current !== sessionId) {
      return;
    }

    const uploadedDocMap = new Map<string, UploadedDocumentInfo>();

    const convertedMessages: Message[] = apiMessages.map(apiMsg => {
      const rawDocuments = Array.isArray(apiMsg.meta_data?.retrieved_documents) ? apiMsg.meta_data.retrieved_documents : [];
      rawDocuments.forEach(doc => {
        const scope = doc?.scope === 'GLOBAL' ? 'GLOBAL' : 'CHAT';
        if (scope !== 'CHAT') {
          return;
        }
        const normalized = normalizeUploadedDocument(doc);
        const key = String(normalized.documentId ?? normalized.id);
        if (!uploadedDocMap.has(key)) {
          uploadedDocMap.set(key, normalized);
        }
      });

      const normalizedRole: Message['role'] = apiMsg.role === 'assistant'
        ? 'assistant'
        : apiMsg.role === 'system'
          ? 'system'
          : 'user';

      return {
        id: apiMsg.id,
        role: normalizedRole,
        content: apiMsg.content ?? '',
        timestamp: new Date(apiMsg.created_at),
        citations: normalizeConversationDocuments(apiMsg.meta_data?.retrieved_documents ?? []),
      };
    });

    const mergedDocumentsMap = new Map<string, UploadedDocumentInfo>();
    (session?.uploadedDocuments ?? []).forEach(doc => {
      const key = String(doc.documentId ?? doc.id);
      mergedDocumentsMap.set(key, doc);
    });
    uploadedDocMap.forEach((doc, key) => {
      if (!mergedDocumentsMap.has(key)) {
        mergedDocumentsMap.set(key, doc);
      }
    });
    const mergedDocuments = Array.from(mergedDocumentsMap.values());

    setMessages(convertedMessages);
    const lastAssistantWithCitations = [...convertedMessages].reverse().find(msg => msg.role === 'assistant' && Array.isArray(msg.citations) && msg.citations.length > 0);
    setLastContextDocuments(lastAssistantWithCitations?.citations ?? []);
    setSessions(prev => prev.map(s =>
      s.id === sessionId
        ? { ...s, messages: convertedMessages, uploadedDocuments: mergedDocuments }
        : s
    ));
  } catch (error) {
    if (activeHistoryRequestRef.current === sessionId) {
      console.error('Failed to load messages from DB:', error);
      if (session?.messages) {
        setMessages(session.messages);
      }
    }
  } finally {
    if (activeHistoryRequestRef.current === sessionId) {
      activeHistoryRequestRef.current = null;
    }
  }
};
  const deleteSession = async (sessionId: string) => {
    try {
      // Delete from database
      await chatApi.deleteSession(sessionId);

      // Update local state
      const updatedSessions = sessions.filter(s => s.id !== sessionId);
      setSessions(updatedSessions);

      if (currentSessionId === sessionId) {
        if (updatedSessions.length > 0) {
          await selectSession(updatedSessions[0].id, updatedSessions[0]);
        } else {
          createNewSession();
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Publish session handlers
  const handleOpenPublishDialog = () => {
    if (currentSession) {
      setPublishTitle(currentSession.title || 'Chat Session');
      setPublishDescription('');
      setPublishError(null);
      setPublishSuccess(false);
      setPublishDialogOpen(true);
    }
  };

  const handleClosePublishDialog = () => {
    setPublishDialogOpen(false);
    setPublishTitle('');
    setPublishDescription('');
    setPublishError(null);
    setPublishSuccess(false);
  };

  const handlePublishSession = async () => {
    if (!currentSessionId || !publishTitle.trim()) {
      setPublishError('Bitte geben Sie einen Titel ein');
      return;
    }

    setPublishing(true);
    setPublishError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `http://localhost:18000/api/v1/chat/sessions/${currentSessionId}/publish`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title: publishTitle.trim(),
            description: publishDescription.trim() || undefined,
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Fehler beim VerÃƒÂ¶ffentlichen');
      }

      await response.json();
      setPublishSuccess(true);

      // Close dialog after 1.5 seconds
      setTimeout(() => {
        handleClosePublishDialog();
      }, 1500);
    } catch (error) {
      console.error('Error publishing session:', error);
      setPublishError(
        error instanceof Error ? error.message : 'Fehler beim VerÃƒÂ¶ffentlichen der Sitzung'
      );
    } finally {
      setPublishing(false);
    }
  };





  const sendMessage = async () => {
  const trimmedMessage = inputMessage.trim();
  const hasMessage = trimmedMessage.length > 0;
  const hasUploads = uploadedFiles.length > 0;

  if (!hasMessage && !hasUploads) {
    return;
  }

  if (loading) {
    return;
  }

  autoScrollRef.current = true;

  let activeSessionId = currentSessionId;
  if (!activeSessionId) {
    const session = await createNewSession();
    activeSessionId = session.id;
  }

  let userMessage: Message | null = null;
  if (hasMessage) {
    userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: trimmedMessage,
      timestamp: new Date(),
      attachments: hasUploads ? [...uploadedFiles] : undefined,
      citations: [],
    };
    setMessages(prev => [...prev, userMessage!]);
    setInputMessage('');
  }

  setLoading(true);

  if (hasMessage && messages.length === 0) {
    const title = trimmedMessage.slice(0, 30) + (trimmedMessage.length > 30 ? '...' : '');
    setSessions(prev => {
      const updated = prev.map(session =>
        session.id === activeSessionId
          ? { ...session, title, updatedAt: new Date() }
          : session
      );
      return updated;
    });
  }

  let uploadOutcome: UploadOutcome = { documents: [], notices: [] };
  if (hasUploads) {
    uploadOutcome = await handleFileUpload();
  }

  const sessionDocuments: UploadedDocumentInfo[] = [
    ...currentSessionDocuments,
    ...uploadOutcome.documents,
  ];

  if (uploadOutcome.documents.length > 0 && activeSessionId) {
    const docsForStorage = sessionDocuments;
    setSessions(prev => {
      const updated = prev.map(session =>
        session.id === activeSessionId
          ? { ...session, uploadedDocuments: docsForStorage, updatedAt: new Date() }
          : session
      );
      return updated;
    });
  }

  if (!hasMessage) {
    const ackContent = buildUploadAcknowledgement(uploadOutcome.notices, uploadOutcome.documents);
    const ackMessage: Message = {
      id: `msg-${Date.now()}-upload`,
      role: 'assistant',
      content: ackContent,
      timestamp: new Date(),
      citations: [],
    };
    setMessages(prev => [...prev, ackMessage]);

    if (activeSessionId) {
      const referencesForSession = sessionDocuments;
      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id !== activeSessionId) return session;
          const updatedMessages = [...(session.messages || [])];
          updatedMessages.push(ackMessage);
          return {
            ...session,
            messages: updatedMessages,
            uploadedDocuments: referencesForSession,
            updatedAt: new Date(),
          };
        });
        return updated;
      });
    }

    setLoading(false);
    setUploadedFiles([]);
    setUploadSuccess([]);
    return;
  }

  const historySource = [...messages];
  if (userMessage) {
    historySource.push(userMessage);
  }
  const conversationHistory: MCPMessage[] = historySource
    .slice(-CONTEXT_WINDOW_SIZE)
    .map(msg => ({
      role: msg.role,
      content: msg.content,
    }));

  if (conversationHistory.length === 0) {
    conversationHistory.push({
      role: 'user',
      content: trimmedMessage,
    });
  }

  const assistantTimestamp = new Date();
  const assistantMessageId = `msg-${assistantTimestamp.getTime()}-assistant`;
  const assistantMessage: Message = {
    id: assistantMessageId,
    role: 'assistant',
    content: '',
    timestamp: assistantTimestamp,
    citations: [],
  };
  setMessages(prev => [...prev, assistantMessage]);

  const normalizedUploadsForContext = sessionDocuments.map(doc => ({
    id: doc.documentId,
    title: doc.title,
    scope: doc.scope,
    content: doc.content,
    content_length: doc.contentLength,
    mime_type: doc.mimeType,
    meta_data: doc.metadata,
  }));

  let streamContent = '';
  let references: ConversationDocument[] = [];

  try {
    const department = user?.primary_department || 'UNKNOWN';

    await mcpClient.streamMessage(conversationHistory, {
      tools: searchEnabled ? ['chat', 'hybrid_search'] : ['chat'],
      rag_enabled: searchEnabled,
      session_id: activeSessionId,
      department,
      uploaded_documents: normalizedUploadsForContext,
      onChunk: (chunk: string) => {
        streamContent += chunk;
        setMessages(prev => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last && last.id === assistantMessageId) {
            next[next.length - 1] = { ...last, content: streamContent };
          }
          return next;
        });
      },
      onDone: (payload: any) => {
        const rawDocuments = Array.isArray(payload?.citations) && payload.citations.length > 0
          ? payload.citations
          : Array.isArray(payload?.documents)
            ? payload.documents
            : [];
        references = normalizeConversationDocuments(rawDocuments);
        setLastContextDocuments(references);
        setMessages(prev => prev.map(message =>
          message.id === assistantMessageId
            ? { ...message, citations: references }
            : message
        ));
      },
      onError: (error: string) => {
        setLastContextDocuments([]);
        setMessages(prev => prev.map(message =>
          message.id === assistantMessageId
            ? { ...message, content: `Error: ${error}` }
            : message
        ));
      },
    });

    if (activeSessionId) {
      const userMsg = userMessage;
      const assistantFinal: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: streamContent,
        timestamp: assistantTimestamp,
        citations: references,
      };
      const docsForStorage = sessionDocuments;

      setSessions(prev => {
        const updated = prev.map(session => {
          if (session.id !== activeSessionId) return session;
          const updatedMessages = [...(session.messages || [])];
          if (userMsg) {
            updatedMessages.push(userMsg);
          }
          updatedMessages.push(assistantFinal);
          return {
            ...session,
            messages: updatedMessages,
            uploadedDocuments: docsForStorage,
            updatedAt: new Date(),
          };
        });
        return updated;
      });
    }
  } catch (error) {
    const fallbackError =
      error instanceof Error ? error.message : 'Fehler bei der Verarbeitung Ihrer Nachricht.';
    setMessages(prev => prev.map(message =>
      message.id === assistantMessageId
        ? { ...message, content: fallbackError }
        : message
    ));
  } finally {
    setLoading(false);
    setUploadedFiles([]);
    setUploadSuccess([]);
  }
};
;





  // Store abort controllers for cleanup





  // Store abort controllers for cleanup


  const abortControllers = React.useRef<AbortController[]>([]);


  const isUploadingRef = React.useRef<boolean>(false);





  const handleFileUpload = async (): Promise<UploadOutcome> => {


    if (uploadedFiles.length === 0) {


      return { documents: [], notices: [] };


    }





    setUploadSuccess([]);





    let activeSessionId = currentSessionId;


    if (!activeSessionId) {


      const session = await createNewSession();


      activeSessionId = session.id;


    }





    setUploading(true);


    isUploadingRef.current = true;





    const uploadedDocuments: UploadedDocumentInfo[] = [];


    const notices: string[] = [];





    abortControllers.current = [];





    const baseUrl = mcpClient.getBaseUrl();


    const uploadUrl = `${baseUrl}/api/v1/documents/upload`;


    const scope: 'GLOBAL' | 'CHAT' = saveToDatabase ? 'GLOBAL' : 'CHAT';





    for (const file of uploadedFiles) {


      const formData = new FormData();


      formData.append('file', file);


      formData.append('scope', scope);


      formData.append('visibility', documentVisibility);


      if (scope === 'CHAT' && activeSessionId) {


        formData.append('session_id', activeSessionId);


      }





      const token = localStorage.getItem('access_token');


      const headers: Record<string, string> = {};


      if (token) {


        headers['Authorization'] = `Bearer ${token}`;


      }





      const abortController = new AbortController();


      abortControllers.current.push(abortController);





      try {


        const response = await fetch(uploadUrl, {


          method: 'POST',


          headers,


          body: formData,


          signal: abortController.signal


        });





        if (!response.ok) {


          const errorText = await response.text();


          let errorMessage = `Upload von ${file.name} fehlgeschlagen: ${response.status}`;


          try {


            const errorJson = JSON.parse(errorText);


            const detail = errorJson.detail?.[0]?.msg || errorJson.detail;


            if (typeof detail === 'string') {


              errorMessage = `Upload von ${file.name} fehlgeschlagen: ${detail}`;


            }


          } catch (parseError) {


            // ignore parse errors


          }


          setUploadSuccess(prev => [...prev, errorMessage]);


          notices.push(errorMessage);


          continue;


        }





        const documentData = await response.json();





        if (documentData.duplicate) {
          // Hole die existing_document_id aus der Response
          const existingDocId = documentData.existing_document_id;

          if (existingDocId) {
            // Erstelle Document-Info mit der RICHTIGEN ID und Content vom Backend
            const duplicateDoc = normalizeUploadedDocument({
              id: existingDocId,
              document_id: existingDocId,
              filename: documentData.filename || file.name,
              original_filename: documentData.original_filename || file.name,
              title: documentData.title || documentData.filename || file.name,
              content: documentData.content,  // Ã¢Å“â€¦ Content vom Backend!
              contentLength: documentData.content_length,
              mimeType: documentData.mime_type,
              fileType: documentData.file_type,
              scope: 'GLOBAL',  // Duplikate sind immer GLOBAL
              metadata: documentData.meta_data,
              created_at: documentData.created_at
            });

            // PrÃƒÂ¼fe ob bereits im aktuellen Session-Kontext
            const alreadyInSession = currentSessionDocuments.some(
              doc => doc.documentId === existingDocId
            );

            if (!alreadyInSession) {
              uploadedDocuments.push(duplicateDoc);
            }
          }

          const duplicateMessage =
            typeof documentData.message === 'string'
              ? documentData.message
              : `${file.name} (bereits vorhanden, wird verwendet)`;

          setUploadSuccess(prev => [...prev, duplicateMessage]);
          notices.push(duplicateMessage);
          continue;
        }





        const responseScope: 'GLOBAL' | 'CHAT' = (documentData.scope as 'GLOBAL' | 'CHAT') || scope;


        const responseMeta: Record<string, any> =


          (documentData.meta_data as Record<string, any>) ||


          (documentData.metadata as Record<string, any>) ||


          {};


        const docMessage =


          typeof documentData.message === 'string'


            ? documentData.message


            : `Upload von ${file.name} erfolgreich (${responseScope === 'GLOBAL' ? 'Firmendatenbank' : 'Chat-Kontext'})`;





        setUploadSuccess(prev => [...prev, docMessage]);


        notices.push(docMessage);





        const content =


          typeof documentData.content === 'string' ? documentData.content : undefined;


        const contentLength =


          typeof documentData.content_length === 'number'


            ? documentData.content_length


            : content?.length;





        const normalizedDoc = normalizeUploadedDocument(documentData, {


          scope: responseScope,


          content,


          contentPreview: typeof documentData.content_preview === 'string' ? documentData.content_preview : undefined,


          contentLength,


          mimeType: documentData.mime_type,


          fileType: documentData.file_type,


          metadata: responseMeta,


          department: documentData.department ?? responseMeta.department,


          accessDepartments: documentData.access_departments ?? responseMeta.allowed_departments,


          uploadedBy: documentData.uploaded_by,


          createdAt: documentData.created_at,


          updatedAt: documentData.updated_at


        });





        uploadedDocuments.push(normalizedDoc);


      } catch (error) {


        if ((error as any)?.name === 'AbortError') {


          const abortMessage = `Upload von ${file.name} abgebrochen`;


          setUploadSuccess(prev => [...prev, abortMessage]);


          notices.push(abortMessage);


        } else {


          const message = error instanceof Error ? error.message : 'Unbekannter Fehler';


          const failureMessage = `Upload von ${file.name} fehlgeschlagen: ${message}`;


          setUploadSuccess(prev => [...prev, failureMessage]);


          notices.push(failureMessage);


        }


      }


    }





    abortControllers.current = [];


    setUploading(false);


    isUploadingRef.current = false;


    setUploadedFiles([]);





    return { documents: uploadedDocuments, notices };


  };










  const openDocumentPreview = async (doc: UploadedDocumentInfo | ConversationDocument) => {
  const baseUrl = mcpClient.getBaseUrl();
  const documentId = doc.documentId || (doc as any).id;
  if (!documentId) {
    setPreviewOpen(false);
    return;
  }

  const source: 'chat' | 'knowledge_base' = (doc as any).source
    ? (doc as any).source
    : doc.scope === 'GLOBAL'
      ? 'knowledge_base'
      : 'chat';

  setPreviewOpen(true);
  setPreviewLoading(true);
  setPreviewError(null);

  const headers: Record<string, string> = {};
  const token = localStorage.getItem('access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const sanitizePreview = (value?: string) =>
    typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : undefined;

  try {
    if (source === 'knowledge_base') {
      const response = await fetch(`${baseUrl}/api/v1/documents/${documentId}`, { headers });
      if (!response.ok) {
        throw new Error(`Vorschau konnte nicht geladen werden (${response.status}).`);
      }

      const detail = await response.json();
      const content = sanitizePreview(detail.content || detail.content_preview);

      setDocumentPreview({
        id: detail.id || documentId,
        title: detail.title || detail.filename || 'Dokument',
        scope: 'GLOBAL',
        source: 'knowledge_base',
        content: content,
        contentPreview: content,
        mimeType: detail.mime_type,
        createdAt: detail.created_at,
        updatedAt: detail.updated_at,
        chunkId: detail.chunk_id,
      });
    } else {
      const response = await fetch(`${baseUrl}/api/v1/chat/files/${documentId}`, { headers });
      if (!response.ok) {
        throw new Error(`Vorschau konnte nicht geladen werden (${response.status}).`);
      }

      const detail = await response.json();
      const content = sanitizePreview(detail.content || detail.content_preview);

      setDocumentPreview({
        id: detail.id || documentId,
        title: detail.title || detail.original_filename || 'Dokument',
        scope: 'CHAT',
        source: 'chat',
        content: content,
        contentPreview: content,
        mimeType: detail.mime_type,
        createdAt: detail.created_at,
        updatedAt: detail.updated_at,
      });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Vorschau konnte nicht geladen werden.';
    setPreviewError(message);
  } finally {
    setPreviewLoading(false);
  }
};
;





  const closeDocumentPreview = () => {


    setPreviewOpen(false);


    setPreviewLoading(false);


    setPreviewError(null);


    setDocumentPreview(null);


  };





  const handleSidebarToggle = () => {
    setSidebarOpen(prev => !prev);
  };

  const handleRemoveUploadedFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleInputChange = (value: string) => {
    setInputMessage(value);
  };

  const handleToggleSearch = () => {
    setSearchEnabled(prev => !prev);
  };

  const handleToggleSaveToDatabase = () => {
    setSaveToDatabase(prev => !prev);
  };

  const handleToggleDocumentVisibility = () => {
    setDocumentVisibility(prev => (prev === 'all' ? 'department' : 'all'));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {


    if (e.target.files) {


      setUploadedFiles(Array.from(e.target.files));


    }


  };





  const handleKeyPress = (e: React.KeyboardEvent<HTMLDivElement>) => {


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





  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: darkMode ? '#1e1e1e' : '#fafafa' }}>
      <Sidebar
        open={sidebarOpen}
        drawerWidth={drawerWidth}
        darkMode={darkMode}
        folders={folders}
        sessions={sessions}
        currentSessionId={currentSessionId}
        isAdmin={isAdmin}
        createNewSession={createNewSession}
        createNewFolder={createNewFolder}
        toggleFolder={toggleFolder}
        editingFolderId={editingFolderId}
        setEditingFolderId={setEditingFolderId}
        newFolderName={newFolderName}
        setNewFolderName={setNewFolderName}
        saveFolderName={saveFolderName}
        deleteFolder={deleteFolder}
        selectSession={selectSession}
        editingTitleId={editingTitleId}
        setEditingTitleId={setEditingTitleId}
        newTitle={newTitle}
        setNewTitle={setNewTitle}
        saveTitle={saveTitle}
        deleteSession={deleteSession}
        moveSessionToFolder={moveSessionToFolder}
        onNavigateDashboard={() => navigate('/dashboard')}
        onLogout={handleLogout}
      />

      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <ChatHeader
          title={currentSession?.title ?? 'Chat'}
          darkMode={darkMode}
          onToggleDarkMode={toggleDarkMode}
          onToggleSidebar={handleSidebarToggle}
          user={user}
          onLogout={handleLogout}
          onPublish={handleOpenPublishDialog}
          canPublish={messages.length > 0}
        />

        {lastContextDocuments.length > 0 && (
          <Box sx={{ px: 3, pt: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Verwendete Dokumente
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {lastContextDocuments.map(doc => (
                <Chip
                  key={`${doc.documentId ?? doc.id}-context`}
                  icon={<InsertDriveFileIcon fontSize="small" />}
                  label={doc.alias ? `${doc.alias} - ${doc.title}` : doc.title}
                  size="small"
                  onClick={() => openDocumentPreview(doc)}
                  sx={{ maxWidth: '100%' }}
                />
              ))}
            </Box>
          </Box>
        )}

        <MessageList
          messages={messages}
          darkMode={darkMode}
          loading={loading}
          user={user}
          onCopy={handleCopy}
          onOpenDocument={openDocumentPreview}
          messagesEndRef={messagesEndRef}
          containerRef={messagesContainerRef}
          onScroll={handleMessagesScroll}
        />

        <ChatInput
          darkMode={darkMode}
          uploadedFiles={uploadedFiles}
          onRemoveUploadedFile={handleRemoveUploadedFile}
          searchEnabled={searchEnabled}
          onToggleSearch={handleToggleSearch}
          saveToDatabase={saveToDatabase}
          onToggleSaveToDatabase={handleToggleSaveToDatabase}
          documentVisibility={documentVisibility}
          onToggleDocumentVisibility={handleToggleDocumentVisibility}
          fileInputRef={fileInputRef}
          onFileSelect={handleFileSelect}
          inputMessage={inputMessage}
          onInputChange={handleInputChange}
          onKeyDown={handleKeyPress}
          loading={loading}
          onSend={sendMessage}
          uploading={uploading}
          uploadSuccess={uploadSuccess}
          currentSessionDocuments={currentSessionDocuments}
          onOpenDocument={openDocumentPreview}
        />
      </Box>

      <Dialog open={previewOpen} onClose={closeDocumentPreview} fullWidth maxWidth="md">
        <DialogTitle>{documentPreview?.title || 'Dokumentvorschau'}</DialogTitle>
        <DialogContent dividers>
          {previewLoading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 160 }}>
              <CircularProgress size={32} />
            </Box>
          ) : previewError ? (
            <Alert severity="error">{previewError}</Alert>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="body2" color="text.secondary">
                {documentPreview?.mimeType || 'Unbekannter Dateityp'}
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  maxHeight: 360,
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'Consolas, \"Courier New\", monospace',
                  fontSize: '0.9rem'
                }}
              >
                {documentPreview?.content || documentPreview?.contentPreview || 'Kein Inhalt verfuegbar.'}
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDocumentPreview}>Schliessen</Button>
        </DialogActions>
      </Dialog>

      {/* Publish Session Dialog */}
      <Dialog
        open={publishDialogOpen}
        onClose={handleClosePublishDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: darkMode ? '#2a2a2a' : '#ffffff',
            border: darkMode ? '1px solid #3d3d3d' : '1px solid #e5e5e5',
          }
        }}
      >
        <DialogTitle sx={{ color: 'text.primary' }}>
          Sitzung als Dokument verÃƒÂ¶ffentlichen
        </DialogTitle>
        <DialogContent>
          {publishSuccess ? (
            <Alert severity="success" sx={{ mt: 2 }}>
              Sitzung erfolgreich verÃƒÂ¶ffentlicht! Das Dokument ist jetzt in der Wissensdatenbank verfÃƒÂ¼gbar.
            </Alert>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                VerÃƒÂ¶ffentlichen Sie diese Chat-Sitzung als durchsuchbares Dokument in der Wissensdatenbank.
              </Typography>

              <TextField
                label="Titel"
                value={publishTitle}
                onChange={(e) => setPublishTitle(e.target.value)}
                fullWidth
                required
                autoFocus
                error={!!publishError && !publishTitle.trim()}
                helperText={!publishTitle.trim() && publishError ? 'Titel ist erforderlich' : ''}
              />

              <TextField
                label="Beschreibung (optional)"
                value={publishDescription}
                onChange={(e) => setPublishDescription(e.target.value)}
                fullWidth
                multiline
                rows={3}
                placeholder="FÃƒÂ¼gen Sie eine Beschreibung hinzu, um anderen zu helfen, dieses Dokument zu finden..."
              />

              {publishError && (
                <Alert severity="error">{publishError}</Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePublishDialog} disabled={publishing}>
            {publishSuccess ? 'SchlieÃƒÅ¸en' : 'Abbrechen'}
          </Button>
          {!publishSuccess && (
            <Button
              onClick={handlePublishSession}
              variant="contained"
              disabled={publishing || !publishTitle.trim()}
              startIcon={publishing ? <CircularProgress size={16} /> : null}
            >
              {publishing ? 'VerÃƒÂ¶ffentliche...' : 'VerÃƒÂ¶ffentlichen'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );


};





export default ChatGPT;








