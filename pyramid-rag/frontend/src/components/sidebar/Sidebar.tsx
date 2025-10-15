import React, { useState } from "react";
import {
  Drawer,
  Box,
  Typography,
  Button,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  IconButton,
  TextField,
  Chip,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import {
  Add as AddIcon,
  CreateNewFolder as CreateFolderIcon,
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Folder as FolderIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Dashboard as DashboardIcon,
  Logout as LogoutIcon,
  DriveFileMove as MoveIcon,
} from "@mui/icons-material";

export interface SidebarFolder {
  id: string;
  name: string;
  color?: string;
  expanded: boolean;
}

export interface SidebarSession {
  id: string;
  title: string;
  folderId?: string;
  isTemporary?: boolean;
}

export interface SidebarProps {
  open: boolean;
  drawerWidth: number;
  darkMode: boolean;
  folders: SidebarFolder[];
  sessions: SidebarSession[];
  currentSessionId: string;
  isAdmin: boolean;
  createNewSession: (folderId?: string, isTemporary?: boolean) => void | Promise<any>;
  createNewFolder: () => void;
  toggleFolder: (folderId: string) => void;
  editingFolderId: string;
  setEditingFolderId: (folderId: string) => void;
  newFolderName: string;
  setNewFolderName: (name: string) => void;
  saveFolderName: (folderId: string) => void;
  deleteFolder: (folderId: string) => void;
  selectSession: (sessionId: string) => void;
  editingTitleId: string;
  setEditingTitleId: (sessionId: string) => void;
  newTitle: string;
  setNewTitle: (title: string) => void;
  saveTitle: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  moveSessionToFolder: (sessionId: string, folderId: string | null) => void;
  onNavigateDashboard: () => void;
  onLogout: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  open,
  drawerWidth,
  darkMode,
  folders,
  sessions,
  currentSessionId,
  isAdmin,
  createNewSession,
  createNewFolder,
  toggleFolder,
  editingFolderId,
  setEditingFolderId,
  newFolderName,
  setNewFolderName,
  saveFolderName,
  deleteFolder,
  selectSession,
  editingTitleId,
  setEditingTitleId,
  newTitle,
  setNewTitle,
  saveTitle,
  deleteSession,
  moveSessionToFolder,
  onNavigateDashboard,
  onLogout,
}) => {
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    sessionId: string;
  } | null>(null);

  const [folderDialogOpen, setFolderDialogOpen] = useState(false);
  const [newFolderDialogName, setNewFolderDialogName] = useState("");

  const handleContextMenu = (event: React.MouseEvent, sessionId: string) => {
    event.preventDefault();
    setContextMenu({
      mouseX: event.clientX - 2,
      mouseY: event.clientY - 4,
      sessionId,
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const handleMoveToFolder = (folderId: string | null) => {
    if (contextMenu) {
      moveSessionToFolder(contextMenu.sessionId, folderId);
      handleCloseContextMenu();
    }
  };

  const handleCreateFolderClick = () => {
    setNewFolderDialogName("Neuer Ordner");
    setFolderDialogOpen(true);
  };

  const handleSaveNewFolder = () => {
    if (newFolderDialogName.trim()) {
      setNewFolderName(newFolderDialogName.trim());
      createNewFolder();
      setFolderDialogOpen(false);
    }
  };

  // Separate sessions into "recent" (no folder) and folders
  const recentSessions = sessions.filter(s => !s.folderId || s.folderId === "default");
  const customFolders = folders.filter(f => f.id !== "default");

  const renderSession = (session: SidebarSession) => (
    <ListItem key={session.id} disablePadding sx={{ mb: 0.25 }}>
      <ListItemButton
        selected={currentSessionId === session.id}
        onClick={() => selectSession(session.id)}
        onContextMenu={(e) => handleContextMenu(e, session.id)}
        sx={{
          borderRadius: "6px",
          py: 0.5,
          minHeight: 32,
          pl: 1,
          "&.Mui-selected": {
            bgcolor: darkMode ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
            "&:hover": {
              bgcolor: darkMode ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)",
            },
          },
          "&:hover": {
            bgcolor: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
          },
        }}
      >
        {editingTitleId === session.id ? (
          <TextField
            size="small"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onBlur={() => saveTitle(session.id)}
            onKeyPress={(e) => e.key === "Enter" && saveTitle(session.id)}
            sx={{ fontSize: "0.85rem" }}
            autoFocus
            fullWidth
          />
        ) : (
          <ListItemText
            primary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Typography
                  variant="body2"
                  noWrap
                  sx={{ fontSize: "0.85rem", color: "text.primary" }}
                >
                  {session.title}
                </Typography>
                {session.isTemporary && (
                  <Chip
                    label="Temp"
                    size="small"
                    sx={{
                      height: 16,
                      fontSize: "0.65rem",
                      bgcolor: darkMode
                        ? "rgba(245, 124, 0, 0.2)"
                        : "rgba(245, 124, 0, 0.1)",
                      color: "#f57c00",
                    }}
                  />
                )}
              </Box>
            }
          />
        )}

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
            transition: "opacity 0.2s",
            "&:hover": { opacity: 1 },
          }}
        >
          <EditIcon sx={{ fontSize: 14 }} />
        </IconButton>

        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            deleteSession(session.id);
          }}
          sx={{
            ml: 0.5,
            opacity: currentSessionId === session.id ? 1 : 0,
            transition: "opacity 0.2s",
            "&:hover": { opacity: 1 },
          }}
        >
          <DeleteIcon sx={{ fontSize: 14 }} />
        </IconButton>
      </ListItemButton>
    </ListItem>
  );

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? drawerWidth : 0,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          bgcolor: darkMode ? "#1a1a1a" : "#ffffff",
          borderRight: darkMode ? "1px solid #2d2d2d" : "1px solid #e5e5e5",
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Typography
          variant="h6"
          sx={{ fontWeight: 400, fontSize: "1.1rem", color: "text.secondary" }}
        >
          Pyramid RAG
        </Typography>
      </Box>

      <Box sx={{ px: 2, pb: 1.5 }}>
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => createNewSession("default", false)}
          sx={{
            justifyContent: "flex-start",
            textTransform: "none",
            bgcolor: "#003d7a",
            color: "white",
            borderRadius: "12px",
            py: 1,
            mb: 1,
            fontSize: "0.9rem",
            "&:hover": {
              bgcolor: "#002855",
            },
          }}
        >
          Neuer Chat
        </Button>

        <Button
          fullWidth
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => createNewSession("default", true)}
          sx={{
            justifyContent: "flex-start",
            textTransform: "none",
            borderColor: "#d9027d",
            color: "#d9027d",
            borderRadius: "12px",
            py: 0.75,
            mb: 1,
            fontSize: "0.85rem",
            "&:hover": {
              borderColor: "#f57c00",
              bgcolor: "rgba(255, 152, 0, 0.08)",
            },
          }}
        >
          Temporarer Chat (30 Tage)
        </Button>

        <Button
          fullWidth
          variant="text"
          startIcon={<CreateFolderIcon />}
          onClick={handleCreateFolderClick}
          sx={{
            justifyContent: "flex-start",
            textTransform: "none",
            color: "text.secondary",
            borderRadius: "12px",
            py: 0.5,
            fontSize: "0.9rem",
            "&:hover": {
              bgcolor: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
            },
          }}
        >
          Neuer Ordner
        </Button>
      </Box>

      <Divider sx={{ mx: 1 }} />

      <List sx={{ flexGrow: 1, overflow: "auto", px: 1, py: 1 }}>
        {/* Recent Sessions Section - Always visible */}
        {recentSessions.length > 0 && (
          <Box sx={{ mb: 0.5 }}>
            <Typography
              variant="caption"
              sx={{
                px: 1,
                py: 0.5,
                display: "block",
                color: "text.secondary",
                fontSize: "0.75rem",
                fontWeight: 500,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Zuletzt verwendet
            </Typography>
            <List sx={{ pl: 0 }}>
              {recentSessions.map(session => renderSession(session))}
            </List>
          </Box>
        )}

        {/* Custom Folders */}
        {customFolders.map((folder) => (
          <Box key={folder.id} sx={{ mb: 0.5 }}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => toggleFolder(folder.id)}
                sx={{
                  borderRadius: "6px",
                  py: 0.5,
                  minHeight: 32,
                  "&:hover": {
                    bgcolor: darkMode
                      ? "rgba(255,255,255,0.05)"
                      : "rgba(0,0,0,0.04)",
                  },
                }}
              >
                <IconButton size="small" sx={{ p: 0, mr: 1 }}>
                  {folder.expanded ? (
                    <ExpandMoreIcon fontSize="small" />
                  ) : (
                    <ChevronRightIcon fontSize="small" />
                  )}
                </IconButton>

                <FolderIcon
                  sx={{ fontSize: 16, mr: 1, color: "text.secondary" }}
                />

                {editingFolderId === folder.id ? (
                  <TextField
                    size="small"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    onBlur={() => saveFolderName(folder.id)}
                    onKeyPress={(e) =>
                      e.key === "Enter" && saveFolderName(folder.id)
                    }
                    sx={{ fontSize: "0.9rem" }}
                    autoFocus
                  />
                ) : (
                  <Typography
                    variant="body2"
                    sx={{
                      flexGrow: 1,
                      fontSize: "0.9rem",
                      color: "text.primary",
                    }}
                  >
                    {folder.name}
                  </Typography>
                )}

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
                    transition: "opacity 0.2s",
                    "&:hover": { opacity: 1 },
                    ".MuiListItemButton-root:hover &": { opacity: 1 },
                  }}
                >
                  <EditIcon sx={{ fontSize: 14 }} />
                </IconButton>

                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteFolder(folder.id);
                  }}
                  sx={{
                    ml: 0.5,
                    opacity: 0,
                    transition: "opacity 0.2s",
                    "&:hover": { opacity: 1 },
                    ".MuiListItemButton-root:hover &": { opacity: 1 },
                  }}
                >
                  <DeleteIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </ListItemButton>
            </ListItem>

            {folder.expanded && (
              <List sx={{ pl: 3 }}>
                {sessions
                  .filter((session) => session.folderId === folder.id)
                  .map((session) => renderSession(session))}
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
            onClick={() => onNavigateDashboard()}
            sx={{
              mb: 0.5,
              textTransform: "none",
              justifyContent: "flex-start",
              color: "text.secondary",
              fontSize: "0.85rem",
              py: 0.5,
              borderRadius: "8px",
              "&:hover": {
                bgcolor: darkMode
                  ? "rgba(255,255,255,0.05)"
                  : "rgba(0,0,0,0.04)",
              },
            }}
          >
            Admin Dashboard
          </Button>
        )}

        <Button
          fullWidth
          variant="text"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          sx={{
            textTransform: "none",
            justifyContent: "flex-start",
            color: "text.secondary",
            fontSize: "0.85rem",
            py: 0.5,
            borderRadius: "8px",
            "&:hover": {
              bgcolor: darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
            },
          }}
        >
          Abmelden
        </Button>
      </Box>

      {/* Context Menu for moving sessions */}
      <Menu
        open={contextMenu !== null}
        onClose={handleCloseContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={() => handleMoveToFolder(null)}>
          <MoveIcon sx={{ mr: 1, fontSize: 18 }} />
          Zu "Zuletzt verwendet" verschieben
        </MenuItem>
        <Divider sx={{ my: 0.5 }} />
        {customFolders.map((folder) => (
          <MenuItem key={folder.id} onClick={() => handleMoveToFolder(folder.id)}>
            <FolderIcon sx={{ mr: 1, fontSize: 18 }} />
            Zu "{folder.name}" verschieben
          </MenuItem>
        ))}
      </Menu>

      {/* Dialog for creating new folder */}
      <Dialog
        open={folderDialogOpen}
        onClose={() => setFolderDialogOpen(false)}
        PaperProps={{
          sx: {
            bgcolor: darkMode ? "#2d2d2d" : "#ffffff",
            minWidth: 400,
          }
        }}
      >
        <DialogTitle sx={{ color: "text.primary" }}>Neuen Ordner erstellen</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Ordnername"
            type="text"
            fullWidth
            variant="outlined"
            value={newFolderDialogName}
            onChange={(e) => setNewFolderDialogName(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSaveNewFolder()}
            sx={{
              mt: 1,
              "& .MuiInputLabel-root": { color: "text.secondary" },
              "& .MuiOutlinedInput-root": {
                color: "text.primary",
                "& fieldset": { borderColor: darkMode ? "#444" : "#ccc" },
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setFolderDialogOpen(false)} sx={{ color: "text.secondary" }}>
            Abbrechen
          </Button>
          <Button
            onClick={handleSaveNewFolder}
            variant="contained"
            sx={{
              bgcolor: "#003d7a",
              "&:hover": { bgcolor: "#002855" },
            }}
          >
            Erstellen
          </Button>
        </DialogActions>
      </Dialog>
    </Drawer>
  );
};

export default Sidebar;
