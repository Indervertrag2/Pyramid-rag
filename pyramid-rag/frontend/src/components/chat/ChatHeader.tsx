import React, { useState } from "react";
import {
  Box,
  IconButton,
  Typography,
  Avatar,
  Menu,
  MenuItem,
  Divider,
} from "@mui/material";
import {
  Menu as MenuIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Logout as LogoutIcon,
  Publish as PublishIcon,
} from "@mui/icons-material";
import type { User } from "../../types";

interface ChatHeaderProps {
  title: string;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onToggleSidebar: () => void;
  user: User | null;
  onLogout: () => void;
  onPublish?: () => void;
  canPublish?: boolean;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({
  title,
  darkMode,
  onToggleDarkMode,
  onToggleSidebar,
  user,
  onLogout,
  onPublish,
  canPublish = false,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => setAnchorEl(null);

  const userInitial = user?.username?.[0]?.toUpperCase() ?? "U";

  return (
    <Box
      sx={{
        borderBottom: darkMode ? "1px solid #2d2d2d" : "1px solid #e5e5e5",
        bgcolor: darkMode ? "#1e1e1e" : "#ffffff",
        px: 3,
        py: 2,
        display: "flex",
        alignItems: "center",
        gap: 2,
      }}
    >
      <IconButton
        onClick={onToggleSidebar}
        size="small"
        sx={{ color: "text.secondary" }}
      >
        <MenuIcon fontSize="small" />
      </IconButton>

      <Typography
        variant="h6"
        sx={{
          flexGrow: 1,
          fontSize: "1rem",
          fontWeight: 400,
          color: "text.primary",
        }}
      >
        {title}
      </Typography>

      {canPublish && onPublish && (
        <IconButton
          onClick={onPublish}
          size="small"
          sx={{
            color: "text.secondary",
            '&:hover': {
              color: 'primary.main'
            }
          }}
          title="Sitzung als Dokument veröffentlichen"
        >
          <PublishIcon fontSize="small" />
        </IconButton>
      )}

      <IconButton
        onClick={onToggleDarkMode}
        size="small"
        sx={{ color: "text.secondary" }}
      >
        {darkMode ? (
          <LightModeIcon fontSize="small" />
        ) : (
          <DarkModeIcon fontSize="small" />
        )}
      </IconButton>

      <Avatar
        sx={{
          bgcolor: "text.secondary",
          cursor: "pointer",
          width: 32,
          height: 32,
          fontSize: "0.85rem",
          borderRadius: "50%",
        }}
        onClick={handleMenuOpen}
      >
        {userInitial}
      </Avatar>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            mt: 1,
            minWidth: 180,
            bgcolor: darkMode ? "#2a2a2a" : "#ffffff",
            border: darkMode ? "1px solid #3d3d3d" : "1px solid #e5e5e5",
          },
        }}
      >
        <MenuItem disabled sx={{ fontSize: "0.85rem" }}>
          {user?.email}
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            handleMenuClose();
            onLogout();
          }}
          sx={{ fontSize: "0.85rem" }}
        >
          <LogoutIcon sx={{ mr: 1, fontSize: 16 }} /> Abmelden
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default ChatHeader;


