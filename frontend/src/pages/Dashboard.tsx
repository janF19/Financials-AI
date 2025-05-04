// src/pages/Dashboard.tsx
import { useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Button, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemSecondaryAction, 
  Chip, 
  CircularProgress
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { fetchDashboardData, fetchReportsSummary } from '../store/slices/dashboardSlice';
import { format } from 'date-fns';

// Simple Chart component using pure CSS
const StatusChart = ({ summary }: { summary: any }) => {
  const total = summary.total_reports || 1; // Avoid division by zero
  const completedPercentage = Math.round((summary.completed_reports / total) * 100);
  const processingPercentage = Math.round((summary.processing_reports / total) * 100);
  const failedPercentage = Math.round((summary.failed_reports / total) * 100);
  
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Report Status Distribution
      </Typography>
      <Box sx={{ display: 'flex', height: 20, width: '100%', borderRadius: 1, overflow: 'hidden' }}>
        <Box
          sx={{
            width: `${completedPercentage}%`,
            bgcolor: 'success.main',
            transition: 'width 0.5s ease',
          }}
        />
        <Box
          sx={{
            width: `${processingPercentage}%`,
            bgcolor: 'warning.main',
            transition: 'width 0.5s ease',
          }}
        />
        <Box
          sx={{
            width: `${failedPercentage}%`,
            bgcolor: 'error.main',
            transition: 'width 0.5s ease',
          }}
        />
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: 'success.main', mr: 1 }} />
          <Typography variant="caption">Completed ({summary.completed_reports})</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: 'warning.main', mr: 1 }} />
          <Typography variant="caption">Processing ({summary.processing_reports})</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: 'error.main', mr: 1 }} />
          <Typography variant="caption">Failed ({summary.failed_reports})</Typography>
        </Box>
      </Box>
    </Box>
  );
};

const Dashboard = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { summary, recentReports, isLoading } = useAppSelector((state) => state.dashboard);
  
  useEffect(() => {    
    dispatch(fetchDashboardData());
    dispatch(fetchReportsSummary());
  }, [dispatch]);
  
  const getStatusChip = (status: string) => {
    switch (status) {
      case 'completed':
        return <Chip size="small" label="Completed" color="success" />;
      case 'processing':
        return <Chip size="small" label="Processing" color="warning" />;
      case 'failed':
        return <Chip size="small" label="Failed" color="error" />;
      default:
        return <Chip size="small" label={status} />;
    }
  };
  
  const handleUploadClick = () => {
    navigate('/process');
  };
  
  const handleViewReportsClick = () => {
    navigate('/reports');
  };
  
  if (isLoading && !recentReports.length) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: 'repeat(2, 1fr)' }} gap={3}>
        {/* Summary Cards */}
        <Box>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Reports Summary
            </Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2, mb: 2 }}>
              <Box>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.light' }}>
                  <Typography variant="h4">{summary.total_reports}</Typography>
                  <Typography variant="body2">Total Reports</Typography>
                </Paper>
              </Box>
              <Box>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light' }}>
                  <Typography variant="h4">{summary.completed_reports}</Typography>
                  <Typography variant="body2">Completed</Typography>
                </Paper>
              </Box>
              <Box>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.light' }}>
                  <Typography variant="h4">{summary.processing_reports}</Typography>
                  <Typography variant="body2">Processing</Typography>
                </Paper>
              </Box>
              <Box>
                <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.light' }}>
                  <Typography variant="h4">{summary.failed_reports}</Typography>
                  <Typography variant="body2">Failed</Typography>
                </Paper>
              </Box>
            </Box>
            
            <StatusChart summary={summary} />
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 'auto', pt: 2 }}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button variant="contained" onClick={handleUploadClick}>
                  Upload New
                </Button>
                <Button variant="contained" color="secondary" onClick={() => navigate('/search')}>
                  Search
                </Button>
              </Box>
              <Button variant="outlined" onClick={handleViewReportsClick}>
                View All Reports
              </Button>
            </Box>
          </Paper>
        </Box>
        
        {/* Recent Reports */}
        <Box>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Recent Reports
            </Typography>
            
            {recentReports.length === 0 ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Typography variant="body1" color="textSecondary">
                  No reports yet. Upload your first document.
                </Typography>
              </Box>
            ) : (
              <List sx={{ width: '100%', bgcolor: 'background.paper', overflow: 'auto', maxHeight: 300 }}>
                {recentReports.map((report) => (
                  <ListItem key={report.id} divider>
                    <ListItemText
                      primary={report.file_name}
                      secondary={format(new Date(report.created_at), 'PPp')}
                    />
                    <ListItemSecondaryAction>
                      {getStatusChip(report.status)}
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            )}
            
            {recentReports.length > 0 && (
              <Button 
                sx={{ mt: 2, alignSelf: 'flex-end' }} 
                onClick={handleViewReportsClick}
              >
                See All
              </Button>
            )}
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard;