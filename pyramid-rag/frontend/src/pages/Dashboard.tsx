import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  LinearProgress,
  AppBar,
  Toolbar,
  IconButton,
  Menu,
  MenuItem,
  Drawer,
  ListItemIcon,
  ListItemButton,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  TextField,
  Select,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Chat as ChatIcon,
  Search as SearchIcon,
  Folder as FolderIcon,
  Settings as SettingsIcon,
  AccountCircle,
  Menu as MenuIcon,
  Description as DescriptionIcon,
  People as PeopleIcon,
  CloudUpload,
  MessageOutlined,
  FolderOutlined,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [userManagementOpen, setUserManagementOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [recentDocuments, setRecentDocuments] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserDepartment, setNewUserDepartment] = useState('Management');
  const [systemStats, setSystemStats] = useState({
    totalDocuments: 0,
    documentsThisWeek: 0,
    totalUsers: 0,
    activeChats: 0,
    storageUsed: 0
  });

  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchSystemStats();
    fetchRecentDocuments();
  }, []);

  useEffect(() => {
    if (userManagementOpen) {
      fetchUsers();
    }
  }, [userManagementOpen]);

  const fetchSystemStats = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:18000/api/v1/system/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSystemStats({
          totalDocuments: data.total_documents || 0,
          documentsThisWeek: data.documents_this_week || 0,
          totalUsers: data.total_users || 0,
          activeChats: data.active_chats || 0,
          storageUsed: Math.round(data.storage_used_gb || 0)
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchRecentDocuments = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:18000/api/v1/documents?limit=5&sort_by=created_at&sort_order=desc', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.documents && data.documents.length > 0) {
          setRecentDocuments(data.documents.map((doc: any) => ({
            id: doc.id,
            name: doc.filename || doc.title,
            type: doc.file_type || 'Document',
            department: doc.department,
            uploadedBy: doc.uploaded_by_name || 'System',
            date: new Date(doc.created_at).toLocaleDateString('de-DE')
          })));
        }
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:18000/api/v1/admin/users', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const handleCreateUser = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:18000/api/v1/admin/users', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: newUserEmail,
          password: newUserPassword,
          department: newUserDepartment,
          is_superuser: false
        })
      });

      if (response.ok) {
        // Reset form and refresh users
        setNewUserEmail('');
        setNewUserPassword('');
        setNewUserDepartment('Management');
        fetchUsers();
      } else {
        const error = await response.json();
        alert(`Fehler beim Erstellen des Benutzers: ${error.detail || 'Unbekannter Fehler'}`);
      }
    } catch (error) {
      console.error('Error creating user:', error);
      alert('Fehler beim Erstellen des Benutzers');
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Sicher, dass Sie diesen Benutzer löschen möchten?')) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:18000/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        fetchUsers();
      }
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
    handleMenuClose();
  };

  const handleFileUpload = async () => {
    if (!selectedFiles) return;

    setUploading(true);

    try {
      const token = localStorage.getItem('access_token');

      // Upload each file
      for (const file of Array.from(selectedFiles)) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('department', user?.primary_department || 'GENERAL');

        await fetch('http://localhost:18000/api/v1/documents/upload-simple', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
      }

      // Refresh data after upload
      await fetchRecentDocuments();
      await fetchSystemStats();

      setUploadDialogOpen(false);
      setSelectedFiles(null);
    } catch (error) {
      console.error('Error uploading files:', error);
    } finally {
      setUploading(false);
    }
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Dokumente', icon: <FolderIcon />, path: '/documents' },
    { text: 'KI-Chat', icon: <ChatIcon />, path: '/chat' },
    { text: 'Suche', icon: <SearchIcon />, path: '/search' },
    { text: 'Einstellungen', icon: <SettingsIcon />, path: '/settings' }
  ];

  if (user?.is_superuser) {
    menuItems.push({ text: 'Administration', icon: <PeopleIcon />, path: '/admin' });
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* App Bar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <IconButton
            size="large"
            edge="start"
            color="inherit"
            onClick={() => setDrawerOpen(true)}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Pyramid RAG Platform
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.full_name} ({user?.primary_department})
          </Typography>
          <IconButton
            size="large"
            onClick={handleProfileMenuOpen}
            color="inherit"
          >
            <AccountCircle />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Profile Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>Profil</MenuItem>
        <MenuItem onClick={handleMenuClose}>Einstellungen</MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>Abmelden</MenuItem>
      </Menu>

      {/* Side Drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        <Box sx={{ width: 250 }} role="presentation">
          <List>
            {menuItems.map((item) => (
              <ListItemButton
                key={item.text}
                onClick={() => {
                  navigate(item.path);
                  setDrawerOpen(false);
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box sx={{ p: 3 }}>
        {/* Welcome Section */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" gutterBottom>
            Willkommen, {user?.full_name}!
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Hier ist Ihre Übersicht über die Pyramid RAG Platform
          </Typography>
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <DescriptionIcon color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{systemStats.totalDocuments}</Typography>
                    <Typography variant="body2" color="text.secondary">Dokumente</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CloudUpload color="success" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{systemStats.documentsThisWeek}</Typography>
                    <Typography variant="body2" color="text.secondary">Diese Woche</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <PeopleIcon color="info" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{systemStats.totalUsers}</Typography>
                    <Typography variant="body2" color="text.secondary">Benutzer</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <MessageOutlined color="warning" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h4">{systemStats.activeChats}</Typography>
                    <Typography variant="body2" color="text.secondary">Aktive Chats</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

        </Grid>

        {/* Recent Documents and User Management */}
        <Grid container spacing={3}>
          {/* Recent Documents - Full Width */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Zuletzt hinzugefügte Dokumente
              </Typography>
              {recentDocuments.length > 0 ? (
                <List>
                  {recentDocuments.map((doc, index) => (
                  <React.Fragment key={doc.id}>
                    <ListItem>
                      <ListItemAvatar>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                          <DescriptionIcon />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={doc.name}
                        secondary={
                          <Box>
                            <Typography variant="body2" component="span">
                              {doc.department} • {doc.uploadedBy} • {doc.date}
                            </Typography>
                            <Chip
                              label={doc.type}
                              size="small"
                              sx={{ ml: 1 }}
                            />
                          </Box>
                        }
                      />
                      <Button size="small">Öffnen</Button>
                    </ListItem>
                    {index < recentDocuments.length - 1 && <Divider />}
                  </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <FolderOutlined sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    Noch keine Dokumente hochgeladen
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<CloudUpload />}
                    onClick={() => setUploadDialogOpen(true)}
                    sx={{ mt: 2 }}
                  >
                    Erste Dokumente hochladen
                  </Button>
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Box>

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => !uploading && setUploadDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Dokumente hochladen</DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <input
              type="file"
              multiple
              onChange={(e) => setSelectedFiles(e.target.files)}
              style={{ width: '100%', padding: '10px', border: '2px dashed #ccc', borderRadius: '4px' }}
            />
          </Box>
          {selectedFiles && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Ausgewählte Dateien ({selectedFiles.length}):
              </Typography>
              {Array.from(selectedFiles).map((file, index) => (
                <Typography key={index} variant="body2" color="text.secondary">
                  • {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </Typography>
              ))}
            </Box>
          )}
          {uploading && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Dateien werden verarbeitet...
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)} disabled={uploading}>
            Abbrechen
          </Button>
          <Button
            onClick={handleFileUpload}
            variant="contained"
            disabled={!selectedFiles || uploading}
          >
            {uploading ? <CircularProgress size={20} /> : 'Hochladen'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* User Management Dialog */}
      <Dialog
        open={userManagementOpen}
        onClose={() => setUserManagementOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Benutzerverwaltung</DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>Neuen Benutzer erstellen</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="E-Mail"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  type="email"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Passwort"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  type="password"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <FormControl fullWidth>
                  <InputLabel>Abteilung</InputLabel>
                  <Select
                    value={newUserDepartment}
                    onChange={(e) => setNewUserDepartment(e.target.value)}
                    label="Abteilung"
                  >
                    <MenuItem value="Management">Management</MenuItem>
                    <MenuItem value="Vertrieb">Vertrieb</MenuItem>
                    <MenuItem value="Marketing">Marketing</MenuItem>
                    <MenuItem value="Entwicklung">Entwicklung</MenuItem>
                    <MenuItem value="Produktion">Produktion</MenuItem>
                    <MenuItem value="Support">Support</MenuItem>
                    <MenuItem value="Personal">Personal</MenuItem>
                    <MenuItem value="Finanzen">Finanzen</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={1}>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleCreateUser}
                  sx={{ height: '100%' }}
                >
                  +
                </Button>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>Bestehende Benutzer</Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>E-Mail</TableCell>
                  <TableCell>Abteilung</TableCell>
                  <TableCell>Rolle</TableCell>
                  <TableCell>Erstellt am</TableCell>
                  <TableCell>Aktionen</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user: any) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{user.department || '-'}</TableCell>
                    <TableCell>
                      {user.is_superuser ? (
                        <Chip label="Admin" color="primary" size="small" />
                      ) : (
                        <Chip label="Benutzer" size="small" />
                      )}
                    </TableCell>
                    <TableCell>{new Date(user.created_at).toLocaleDateString('de-DE')}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.email === 'admin@pyramid-computer.de'}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserManagementOpen(false)}>Schließen</Button>
        </DialogActions>
      </Dialog>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        onClick={() => navigate('/chat')}
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
        }}
      >
        <ChatIcon />
      </Fab>
    </Box>
  );
};

export default Dashboard;