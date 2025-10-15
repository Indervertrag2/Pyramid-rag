import React from 'react';

import {
  Box,
  Avatar,
  Paper,
  Chip,
  Typography,
  IconButton,
  CircularProgress,
} from '@mui/material';
import {
  AttachFile as AttachFileIcon,
  InsertDriveFile as InsertDriveFileIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import type { ConversationDocument, Message, User } from '../../types';

interface MessageListProps {
  messages: Message[];
  darkMode: boolean;
  loading: boolean;
  user: User | null;
  onCopy: (content: string) => void;
  onOpenDocument: (doc: ConversationDocument) => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  containerRef: React.RefObject<HTMLDivElement>;
  onScroll?: (event: React.UIEvent<HTMLDivElement>) => void;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  darkMode,
  loading,
  user,
  onCopy,
  onOpenDocument,
  messagesEndRef,
  containerRef,
  onScroll,
}) => {
  const userInitial = user?.username?.[0]?.toUpperCase() ?? 'U';

  return (
    <Box
      ref={containerRef}
      onScroll={onScroll}
      sx={{
        flexGrow: 1,
        overflow: 'auto',
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 800 }}>
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 10 }}>
            <Typography variant='h4' gutterBottom sx={{ fontWeight: 300 }}>
              Wie kann ich Ihnen helfen?
            </Typography>
            <Typography variant='body1' color='text.secondary'>
              Stellen Sie Fragen, laden Sie Dokumente hoch oder erkunden Sie die Plattform
            </Typography>
          </Box>
        ) : (
          <>
            {messages.map(message => (
              <Box
                key={message.id}
                sx={{
                  mb: 3,
                  display: 'flex',
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                {message.role !== 'user' && (
                  <Avatar
                    sx={{
                      bgcolor: '#10a37f',
                      mr: 2,
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                    }}
                  >
                    AI
                  </Avatar>
                )}

                <Paper
                  sx={{
                    p: 2,
                    maxWidth: '70%',
                    bgcolor:
                      message.role === 'user'
                        ? darkMode
                          ? '#4a5568'
                          : '#e3f2fd'
                        : darkMode
                          ? '#2d3748'
                          : 'white',
                    borderRadius: '16px',
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
                          size='small'
                          icon={<AttachFileIcon />}
                          sx={{ mr: 1, mb: 1 }}
                        />
                      ))}
                    </Box>
                  )}

                  {message.citations && message.citations.length > 0 && (
                    <Box sx={{ mt: 1.5 }}>
                      <Typography
                        variant='caption'
                        sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}
                      >
                        Referenzierte Dokumente:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {message.citations.map(doc => (
                          <Chip
                            key={`${doc.source}-${doc.documentId ?? doc.id}-${doc.chunkId ?? 'root'}`}
                            icon={<InsertDriveFileIcon />}
                            label={doc.alias ? `${doc.alias} - ${doc.title}` : doc.title}
                            size='small'
                            onClick={() => onOpenDocument(doc)}
                            sx={{ maxWidth: '100%' }}
                          />
                        ))}
                      </Box>
                    </Box>
                  )}

                  {message.role === 'assistant' && (
                    <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                      <IconButton size='small' onClick={() => onCopy(message.content)}>
                        <CopyIcon fontSize='small' />
                      </IconButton>
                    </Box>
                  )}
                </Paper>

                {message.role === 'user' && (
                  <Avatar
                    sx={{
                      bgcolor: 'primary.main',
                      ml: 2,
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                    }}
                  >
                    {userInitial}
                  </Avatar>
                )}
              </Box>
            ))}

            {loading && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <Avatar sx={{ bgcolor: '#10a37f', width: 32, height: 32 }}>AI</Avatar>
                <CircularProgress size={20} />
              </Box>
            )}
          </>
        )}

        <div ref={messagesEndRef} />
      </Box>
    </Box>
  );
};

export default MessageList;
