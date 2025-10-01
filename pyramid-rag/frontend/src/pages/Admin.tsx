import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Tooltip
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Person as PersonIcon,
  Description as DocumentIcon,
  Settings as SettingsIcon,
  // Search as SearchIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Admin: React.FC = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [users, setUsers] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // User management state
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [newUser, setNewUser] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    primary_department: 'Support',
    is_active: true,
    is_superuser: false
  });

  const departments = [
    'Management', 'Vertrieb', 'Marketing', 'Entwicklung',
    'Produktion', 'Qualitätssicherung', 'Support', 'Personal', 'Finanzen'
  ];

  useEffect(() => {
    // Check if user is admin
    if (!user?.is_superuser) {
      navigate('/dashboard');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      // Fetch users
      const usersRes = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/v1/users`,
        config
      );
      setUsers(usersRes.data);

      // Fetch documents
      const docsRes = await axios.get(
        `${import.meta.env.VITE_API_URL}/api/v1/documents?limit=100`,
        config
      );
      setDocuments(docsRes.data);

      // Fetch stats
      try {
        const statsRes = await axios.get(
          `${import.meta.env.VITE_API_URL}/api/v1/admin/stats`,
          config
        );
        setStats(statsRes.data);
      } catch (e) {
        // Stats endpoint might not exist yet
        setStats({
          total_users: usersRes.data.length,
          total_documents: docsRes.data.length,
          total_chats: 0
        });
      }

    } catch (error: any) {
      console.error('Error fetching admin data:', error);
      setError(error.message || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/v1/users`,
        newUser,
        config
      );

      setUserDialogOpen(false);
      setNewUser({
        email: '',
        username: '',
        full_name: '',
        password: '',
        primary_department: 'Support',
        is_active: true,
        is_superuser: false
      });
      fetchData();
    } catch (error: any) {
      console.error('Error creating user:', error);
      setError(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateUser = async (userId: string, updates: any) => {
    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      await axios.patch(
        `${import.meta.env.VITE_API_URL}/api/v1/users/${userId}`,
        updates,
        config
      );

      fetchData();
    } catch (error: any) {
      console.error('Error updating user:', error);
      setError(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) {
      return;
    }

    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      await axios.delete(
        `${import.meta.env.VITE_API_URL}/api/v1/users/${userId}`,
        config
      );

      fetchData();
    } catch (error: any) {
      console.error('Error deleting user:', error);
      setError(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      await axios.delete(
        `${import.meta.env.VITE_API_URL}/api/v1/documents/${docId}`,
        config
      );

      fetchData();
    } catch (error: any) {
      console.error('Error deleting document:', error);
      setError(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  const handleReprocessDocument = async (docId: string) => {
    if (!confirm('Reprocess this document? This will regenerate chunks and embeddings.')) {
      return;
    }

    try {
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/v1/documents/${docId}/reprocess`,
        {},
        config
      );

      setSuccess('Document reprocessing started successfully');
      setTimeout(() => {
        setSuccess(null);
        fetchData(); // Refresh data after a delay
      }, 3000);
    } catch (error: any) {
      console.error('Error reprocessing document:', error);
      setError(error.response?.data?.detail || 'Failed to reprocess document');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Users
              </Typography>
              <Typography variant="h4">
                {stats.total_users || users.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Documents
              </Typography>
              <Typography variant="h4">
                {stats.total_documents || documents.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Chats
              </Typography>
              <Typography variant="h4">
                {stats.total_chats || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={(_e, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab icon={<PersonIcon />} label="Users" />
          <Tab icon={<DocumentIcon />} label="Documents" />
          <Tab icon={<SettingsIcon />} label="Settings" />
        </Tabs>

        {/* Users Tab */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="h6">User Management</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setUserDialogOpen(true)}
            >
              Add User
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Email</TableCell>
                  <TableCell>Username</TableCell>
                  <TableCell>Full Name</TableCell>
                  <TableCell>Department</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.full_name}</TableCell>
                    <TableCell>{user.primary_department}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_superuser ? 'Admin' : 'User'}
                        color={user.is_superuser ? 'secondary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Active' : 'Inactive'}
                        color={user.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => {
                          setEditingUser(user);
                          setUserDialogOpen(true);
                        }}>
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteUser(user.id)}
                          disabled={user.email === 'admin@pyramid-computer.de'}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Documents Tab */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="h6">Document Management</Typography>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={fetchData}
            >
              Refresh
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Department</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Processed</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>{doc.title || doc.filename}</TableCell>
                    <TableCell>{doc.file_type}</TableCell>
                    <TableCell>{doc.department}</TableCell>
                    <TableCell>{(doc.file_size / 1024).toFixed(1)} KB</TableCell>
                    <TableCell>
                      <Chip
                        label={doc.processed ? 'Yes' : 'No'}
                        color={doc.processed ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Reprocess">
                        <IconButton
                          size="small"
                          onClick={() => handleReprocessDocument(doc.id)}
                        >
                          <RefreshIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Reprocess">
                        <IconButton
                          size="small"
                          onClick={() => handleReprocessDocument(doc.id)}
                          disabled={!doc.processed && !doc.error_message}
                        >
                          <RefreshIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteDocument(doc.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Settings Tab */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            System Settings
          </Typography>
          <Alert severity="info">
            Settings configuration coming soon. Use environment variables for now.
          </Alert>
        </TabPanel>
      </Paper>

      {/* User Dialog */}
      <Dialog open={userDialogOpen} onClose={() => {
        setUserDialogOpen(false);
        setEditingUser(null);
      }} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingUser ? 'Edit User' : 'Create New User'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Email"
            value={editingUser?.email || newUser.email}
            onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
            margin="normal"
            disabled={!!editingUser}
          />
          <TextField
            fullWidth
            label="Username"
            value={editingUser?.username || newUser.username}
            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Full Name"
            value={editingUser?.full_name || newUser.full_name}
            onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
            margin="normal"
          />
          {!editingUser && (
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              margin="normal"
            />
          )}
          <FormControl fullWidth margin="normal">
            <InputLabel>Department</InputLabel>
            <Select
              value={editingUser?.primary_department || newUser.primary_department}
              onChange={(e) => setNewUser({ ...newUser, primary_department: e.target.value })}
              label="Department"
            >
              {departments.map(dept => (
                <MenuItem key={dept} value={dept}>{dept}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setUserDialogOpen(false);
            setEditingUser(null);
          }}>
            Cancel
          </Button>
          <Button
            onClick={editingUser ? () => handleUpdateUser(editingUser.id, newUser) : handleCreateUser}
            variant="contained"
          >
            {editingUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Admin;