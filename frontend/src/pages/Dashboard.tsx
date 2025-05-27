// src/pages/Dashboard.tsx
import { Box, Paper, Typography, Button } from '@mui/material';
// import { useNavigate } from 'react-router-dom'; // Can be added back when actions are implemented

const Dashboard = () => {
  // const navigate = useNavigate(); // For future quick actions

  // Placeholder content for the new dashboard features
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Usage Tracking
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Shows reports used vs. monthly limit. (Coming Soon)
        </Typography>
        {/* Placeholder for usage chart or stats */}
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Credit Management
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Purchase additional credits, view balance. (Coming Soon)
        </Typography>
        <Button variant="contained" sx={{ mr: 1 }} disabled>Purchase Credits</Button>
        <Typography variant="body2" component="span" sx={{ mr: 2 }}>Current Balance: --- credits</Typography>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Billing Overview
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Current plan, next billing date. (Coming Soon)
        </Typography>
        <Typography variant="body2">Current Plan: ---</Typography>
        <Typography variant="body2">Next Billing Date: ---</Typography>
      </Paper>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Activity Feed
        </Typography>
        <Typography variant="body1" color="textSecondary" paragraph>
          Recent actions and report generation. (Coming Soon)
        </Typography>
        {/* Placeholder for activity list */}
      </Paper>

      <Paper sx={{ p: 2}}>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Button variant="outlined" sx={{ mr: 1 }} disabled>Buy Credits</Button>
        <Button variant="outlined" sx={{ mr: 1 }} disabled>Upgrade Plan</Button>
        <Button variant="outlined" disabled>Get Help</Button>
      </Paper>

    </Box>
  );
};

export default Dashboard;