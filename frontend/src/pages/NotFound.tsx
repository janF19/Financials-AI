// src/pages/NotFound.tsx
import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined';

const NotFound: React.FC = () => {
  return (
    <Container component="main" maxWidth="sm" sx={{ textAlign: 'center', mt: 8 }}>
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <ReportProblemOutlinedIcon sx={{ fontSize: 80, color: 'warning.main', mb: 2 }} />
        <Typography component="h1" variant="h4" gutterBottom>
          404 - Page Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Oops! The page you are looking for does not exist. It might have been moved or deleted.
        </Typography>
        <Button
          variant="contained"
          component={RouterLink}
          to="/dashboard" // Link back to the main dashboard
        >
          Go to Dashboard
        </Button>
      </Box>
    </Container>
  );
};

export default NotFound;