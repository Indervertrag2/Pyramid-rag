import React from 'react';
import { Outlet } from 'react-router-dom';
import { Box, Typography } from '@mui/material';

const Layout: React.FC = () => {
  return (
    <Box>
      <Typography variant="h6" sx={{ p: 2, bgcolor: 'primary.main', color: 'white' }}>
        Pyramid RAG Platform
      </Typography>
      <Box sx={{ p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;