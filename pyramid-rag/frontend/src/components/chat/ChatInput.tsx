import React from "react";
import {
  Box,
  Chip,
  Typography,
  TextField,
  IconButton,
  Tooltip,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import {
  Search as SearchIcon,
  Business as CompanyIcon,
  Chat as ChatOnlyIcon,
  Public as PublicIcon,
  Group as GroupIcon,
  AttachFile as AttachFileIcon,
  Send as SendIcon,
  InsertDriveFile as InsertDriveFileIcon,
} from "@mui/icons-material";
import type { UploadedDocumentInfo } from "../../types";

type DocumentVisibility = "department" | "all";

interface ChatInputProps {
  darkMode: boolean;
  uploadedFiles: File[];
  onRemoveUploadedFile: (index: number) => void;
  searchEnabled: boolean;
  onToggleSearch: () => void;
  saveToDatabase: boolean;
  onToggleSaveToDatabase: () => void;
  documentVisibility: DocumentVisibility;
  onToggleDocumentVisibility: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => void;
  inputMessage: string;
  onInputChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => void;
  loading: boolean;
  onSend: () => void;
  uploading: boolean;
  uploadSuccess: string[];
  currentSessionDocuments: UploadedDocumentInfo[];
  onOpenDocument: (doc: UploadedDocumentInfo) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  darkMode,
  uploadedFiles,
  onRemoveUploadedFile,
  searchEnabled,
  onToggleSearch,
  saveToDatabase,
  onToggleSaveToDatabase,
  documentVisibility,
  onToggleDocumentVisibility,
  fileInputRef,
  onFileSelect,
  inputMessage,
  onInputChange,
  onKeyDown,
  loading,
  onSend,
  uploading,
  uploadSuccess,
  currentSessionDocuments,
  onOpenDocument,
}) => {
  const handleAddFilesClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <Box
      sx={{
        p: 2,
        borderTop: darkMode ? "1px solid #333" : "1px solid #e0e0e0",
        bgcolor: darkMode ? "#1e1e1e" : "white",
      }}
    >
      <Box sx={{ maxWidth: 1200, mx: "auto" }}>
        {uploadedFiles.length > 0 && (
          <Box sx={{ mb: 2, display: "flex", gap: 1, flexWrap: "wrap" }}>
            {uploadedFiles.map((file, idx) => (
              <Chip
                key={idx}
                label={file.name}
                onDelete={() => onRemoveUploadedFile(idx)}
                icon={<AttachFileIcon />}
                color="primary"
              />
            ))}
          </Box>
        )}

        <Box
          sx={{
            mb: 2,
            display: "flex",
            gap: 2,
            justifyContent: "flex-start",
            flexWrap: "wrap",
          }}
        >
          <Chip
            icon={<SearchIcon />}
            label="Suche"
            onClick={onToggleSearch}
            variant={searchEnabled ? "filled" : "outlined"}
            size="medium"
            sx={{
              minWidth: "160px",
              height: 38,
              "& .MuiChip-icon": {
                fontSize: "1.2rem",
                color: searchEnabled ? "white" : darkMode ? "white" : "inherit",
              },
              "& .MuiChip-label": {
                px: 1.5,
                fontSize: "0.95rem",
                fontWeight: 500,
              },
              bgcolor: searchEnabled ? "#003d7a" : "transparent",
              color: searchEnabled
                ? "white"
                : darkMode
                  ? "white"
                  : "text.primary",
              borderColor: searchEnabled
                ? "#003d7a"
                : darkMode
                  ? "rgba(255,255,255,0.3)"
                  : "divider",
              borderWidth: 2,
              "&:hover": {
                bgcolor: searchEnabled ? "#002855" : "action.hover",
                borderColor: "#003d7a",
              },
              transition: "all 0.2s ease",
            }}
          />

          {uploadedFiles.length > 0 && (
            <>
              <Chip
                icon={saveToDatabase ? <CompanyIcon /> : <ChatOnlyIcon />}
                label={saveToDatabase ? "Firmendatenbank" : "Chat-Kontext"}
                onClick={onToggleSaveToDatabase}
                variant={saveToDatabase ? "filled" : "outlined"}
                size="medium"
                sx={{
                  minWidth: "160px",
                  height: 38,
                  "& .MuiChip-icon": {
                    fontSize: "1.2rem",
                    color: saveToDatabase
                      ? "white"
                      : darkMode
                        ? "white"
                        : "inherit",
                  },
                  "& .MuiChip-label": {
                    px: 1.5,
                    fontSize: "0.95rem",
                    fontWeight: 500,
                  },
                  bgcolor: saveToDatabase ? "#003d7a" : "transparent",
                  color: saveToDatabase
                    ? "white"
                    : darkMode
                      ? "white"
                      : "text.primary",
                  borderColor: saveToDatabase
                    ? "#003d7a"
                    : darkMode
                      ? "rgba(255,255,255,0.3)"
                      : "divider",
                  borderWidth: 2,
                  "&:hover": {
                    bgcolor: saveToDatabase ? "#002855" : "action.hover",
                    borderColor: "#003d7a",
                  },
                  transition: "all 0.2s ease",
                }}
              />

              {saveToDatabase && (
                <Chip
                  icon={
                    documentVisibility === "all" ? (
                      <PublicIcon />
                    ) : (
                      <GroupIcon />
                    )
                  }
                  label={
                    documentVisibility === "all" ? "Alle" : "Nur Abteilung"
                  }
                  onClick={onToggleDocumentVisibility}
                  variant={documentVisibility === "all" ? "filled" : "outlined"}
                  size="medium"
                  sx={{
                    minWidth: "160px",
                    height: 38,
                    "& .MuiChip-icon": {
                      fontSize: "1.2rem",
                      color:
                        documentVisibility === "all"
                          ? "white"
                          : darkMode
                            ? "white"
                            : "inherit",
                    },
                    "& .MuiChip-label": {
                      px: 1.5,
                      fontSize: "0.95rem",
                      fontWeight: 500,
                    },
                    bgcolor:
                      documentVisibility === "all" ? "#003d7a" : "transparent",
                    color:
                      documentVisibility === "all"
                        ? "white"
                        : darkMode
                          ? "white"
                          : "text.primary",
                    borderColor:
                      documentVisibility === "all"
                        ? "#003d7a"
                        : darkMode
                          ? "rgba(255,255,255,0.3)"
                          : "divider",
                    borderWidth: 2,
                    "&:hover": {
                      bgcolor:
                        documentVisibility === "all"
                          ? "#002855"
                          : "action.hover",
                      borderColor: "#003d7a",
                    },
                    transition: "all 0.2s ease",
                  }}
                />
              )}
            </>
          )}
        </Box>

        <Box
          sx={{
            display: "flex",
            gap: 1.5,
            alignItems: "center",
            width: "100%",
          }}
        >
          <input
            type="file"
            multiple
            ref={fileInputRef}
            onChange={onFileSelect}
            style={{ display: "none" }}
            accept=".txt,.pdf,.docx,.xlsx,.pptx,.md,.json,.csv,.xml,.html"
          />

          <Tooltip title="Dateien anhaengen">
            <IconButton
              onClick={handleAddFilesClick}
              sx={{
                color: darkMode ? "grey.400" : "grey.600",
                "&:hover": { color: "#003d7a" },
                alignSelf: "center",
                mb: 0.5,
              }}
            >
              <AttachFileIcon />
            </IconButton>
          </Tooltip>

          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              uploadedFiles.length > 0
                ? "Beschreibe deine Dateien oder stelle eine Frage..."
                : "Nachricht eingeben..."
            }
            disabled={loading}
            sx={{
              flexGrow: 1,
              "& .MuiOutlinedInput-root": {
                borderRadius: "24px",
                bgcolor: darkMode ? "#2a2a2a" : "#f5f5f5",
                pr: 0.5,
                "&:hover fieldset": {
                  borderColor: "#003d7a",
                },
                "&.Mui-focused fieldset": {
                  borderColor: "#003d7a",
                  borderWidth: 2,
                },
              },
            }}
            InputProps={{
              endAdornment: (
                <IconButton
                  onClick={onSend}
                  disabled={
                    loading ||
                    (!inputMessage.trim() && uploadedFiles.length === 0)
                  }
                  sx={{
                    bgcolor: loading ? "transparent" : "#003d7a",
                    color: loading ? "grey.500" : "white",
                    borderRadius: "50%",
                    mr: 0.5,
                    "&:hover": { bgcolor: loading ? "transparent" : "#002855" },
                    "&:disabled": {
                      bgcolor: "action.disabledBackground",
                      color: "action.disabled",
                    },
                  }}
                >
                  {loading ? <CircularProgress size={24} /> : <SendIcon />}
                </IconButton>
              ),
            }}
          />
        </Box>

        {uploading && (
          <Box sx={{ mt: 1 }}>
            <LinearProgress />
            <Typography variant="caption">
              Dateien werden hochgeladen...
            </Typography>
          </Box>
        )}

        {uploadSuccess.length > 0 && (
          <Box sx={{ mt: 1 }}>
            {uploadSuccess.map((message, idx) => (
              <Typography
                key={idx}
                variant="caption"
                sx={{
                  display: "block",
                  color: message.includes("fehlgeschlagen")
                    ? "error.main"
                    : "success.main",
                  fontSize: "0.75rem",
                }}
              >
                {message}
              </Typography>
            ))}
          </Box>
        )}

        {currentSessionDocuments.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography
              variant="caption"
              sx={{ color: "text.secondary", fontSize: "0.7rem", mb: 0.5 }}
            >
              Verfuegbare Dateien in dieser Session:
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              {currentSessionDocuments.map((doc) => (
                <Chip
                  key={doc.id}
                  icon={<InsertDriveFileIcon />}
                  label={doc.title}
                  onClick={() => onOpenDocument(doc)}
                  sx={{ maxWidth: "100%" }}
                />
              ))}
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default ChatInput;

