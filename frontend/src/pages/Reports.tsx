// src/pages/Reports.tsx
import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TablePagination,
  IconButton,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import { Download as DownloadIcon, Delete as DeleteIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { fetchReports, downloadReport, deleteReport } from '../store/slices/reportSlice';
import { fetchRecentReportsData, fetchReportsSummary } from '../store/slices/reportsSummarySlice';
import { Report } from '../types/index';

// Define the type for the data returned by fetchReports().unwrap()
interface FetchedReportsPayload {
  reports: Report[];
  total: number;
  // Add other properties if your API and thunk return more and you need to access them here
}

const ConfirmationDialog = ({ open, onClose, onConfirm, title, content }: { open: boolean, onClose: () => void, onConfirm: () => void, title: string, content: string }) => {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{content}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onConfirm} color="error">
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
};

// Add this helper function to safely format dates
const safeFormatDate = (dateString: string | null | undefined) => {
  if (!dateString) return 'N/A';
  
  try {
    return format(new Date(dateString), 'Pp');
  } catch (error) {
    console.error('Invalid date format:', dateString);
    return 'Invalid date';
  }
};

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

const Reports = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const {
    reports = [],
    totalCount = 0,
    isLoading: isReportsLoading,
    error: reportsError,
    downloadingId
  } = useAppSelector((state) => state.reports);

  const {
    summary,
    recentReports,
    isLoading: isSummaryLoading,
    error: summaryError
  } = useAppSelector((state) => state.reportsSummary);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>(''); // 'all', 'pending', 'processed', 'failed'
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reportToDelete, setReportToDelete] = useState<Report | null>(null);

  const fetchReportsData = () => {
    const params: any = { page: page + 1, limit: rowsPerPage };
    if (statusFilter && statusFilter !== 'all') {
      params.status = statusFilter;
    }
    console.log('Fetching reports with params:', params);
    dispatch(fetchReports(params))
      .unwrap()
      .then((data: FetchedReportsPayload) => {
        console.log('Reports fetch successful:', data);
      })
      .catch((err: any) => {
        console.error('Reports fetch error:', err);
      });
  }

  useEffect(() => {
    dispatch(fetchRecentReportsData());
    dispatch(fetchReportsSummary());
    fetchReportsData();
  }, [dispatch, page, rowsPerPage, statusFilter]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0); // Reset to first page
  };

   const handleStatusFilterChange = (event: SelectChangeEvent<string>) => {
      setStatusFilter(event.target.value as string);
      setPage(0); // Reset to first page when filter changes
    };

  const handleDownload = (id: string) => {
    dispatch(downloadReport(id));
  };

  const handleDeleteClick = (report: Report) => {
    setReportToDelete(report);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setReportToDelete(null);
  };

  const handleConfirmDelete = () => {
    if (reportToDelete) {
      dispatch(deleteReport(reportToDelete.id)).then(() => {
        // Optionally refetch data if pagination might be affected
        if(reports.length === 1 && page > 0) {
          setPage(page - 1);
        } else {
          fetchReportsData(); // Refetch current page
        }
      });
    }
    handleCloseDialog();
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'processed':
        return <Chip size="small" label="Processed" color="success" />;
      case 'pending':
        return <Chip size="small" label="Pending" color="warning" />;
      case 'failed':
        return <Chip size="small" label="Failed" color="error" />;
      default:
        return <Chip size="small" label={status} />;
    }
  };

  const handleUploadClick = () => {
    navigate('/process');
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Reports Overview
      </Typography>

      {isSummaryLoading && !summary.total_reports && (
         <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}>
           <CircularProgress />
         </Box>
      )}
      {!isSummaryLoading && summaryError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load summary: {summaryError}
        </Alert>
      )}
      {!isSummaryLoading && !summaryError && summary.total_reports !== undefined && (
        <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: 'repeat(2, 1fr)' }} gap={3} sx={{ mb: 4 }}>
          <Box>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Typography variant="h6" gutterBottom>
                Reports Summary
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2, mb: 2 }}>
                <Box>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.light' }}>
                    <Typography variant="h4">{summary.total_reports || 0}</Typography>
                    <Typography variant="body2">Total Reports</Typography>
                  </Paper>
                </Box>
                <Box>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light' }}>
                    <Typography variant="h4">{summary.completed_reports || 0}</Typography>
                    <Typography variant="body2">Completed</Typography>
                  </Paper>
                </Box>
                <Box>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'warning.light' }}>
                    <Typography variant="h4">{summary.processing_reports || 0}</Typography>
                    <Typography variant="body2">Processing</Typography>
                  </Paper>
                </Box>
                <Box>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.light' }}>
                    <Typography variant="h4">{summary.failed_reports || 0}</Typography>
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
              </Box>
            </Paper>
          </Box>

          <Box>
            <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Typography variant="h6" gutterBottom>
                Recent Reports
              </Typography>
              {isSummaryLoading && recentReports.length === 0 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1 }}>
                    <CircularProgress />
                </Box>
              )}
              {!isSummaryLoading && recentReports.length === 0 && !summaryError && (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1, textAlign: 'center' }}>
                  <Typography variant="body1" color="textSecondary">
                    No recent reports found. <br/>Upload a document to get started.
                  </Typography>
                </Box>
              )}
              {!isSummaryLoading && recentReports.length > 0 && (
                <List sx={{ width: '100%', bgcolor: 'background.paper', overflow: 'auto', maxHeight: 300 /* Adjust as needed */ }}>
                  {recentReports.map((report: Report) => (
                    <ListItem key={report.id} divider>
                      <ListItemText
                        primary={report.file_name}
                        secondary={report.created_at ? format(new Date(report.created_at), 'PPp') : 'N/A'}
                      />
                      <ListItemSecondaryAction>
                        {getStatusChip(report.status)}
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              )}
            </Paper>
          </Box>
        </Box>
      )}

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        All Reports
      </Typography>

      {reportsError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {reportsError}
        </Alert>
      )}

       <Paper sx={{ mb: 2, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
         <FormControl sx={{ minWidth: 150 }} size="small">
           <InputLabel id="status-filter-label">Filter by Status</InputLabel>
           <Select
             labelId="status-filter-label"
             id="status-filter"
             value={statusFilter}
             label="Filter by Status"
             onChange={handleStatusFilterChange}
           >
             <MenuItem value="all">All Statuses</MenuItem>
             <MenuItem value="pending">pending</MenuItem>
             <MenuItem value="processed">processed</MenuItem>
             <MenuItem value="failed">Failed</MenuItem>
           </Select>
         </FormControl>
          <Tooltip title="Refresh List">
              <IconButton onClick={fetchReportsData} disabled={isReportsLoading}>
                  <RefreshIcon />
              </IconButton>
          </Tooltip>
       </Paper>

      <Paper>
        <TableContainer>
          <Table stickyHeader aria-label="reports table">
            <TableHead>
              <TableRow>
                <TableCell>File Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell>Updated At</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isReportsLoading && (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              )}
              {!isReportsLoading && reports.length === 0 && (
                 <TableRow>
                   <TableCell colSpan={5} align="center">
                      No reports found. {statusFilter !== 'all' && statusFilter !== '' ? 'Try adjusting the filter.' : 'Upload a document to get started.'}
                   </TableCell>
                 </TableRow>
              )}
              {!isReportsLoading &&
                reports.map((report: Report) => (
                  <TableRow hover key={report.id}>
                    <TableCell>{report.file_name}</TableCell>
                    <TableCell>{getStatusChip(report.status)}</TableCell>
                    <TableCell>
                      {safeFormatDate(report.created_at)}
                    </TableCell>
                     <TableCell>
                      {safeFormatDate(report.updated_at)}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={report.status !== 'processed' ? 'Report must be processed to download' : 'Download Report'}>
                        <span>
                          <IconButton
                            onClick={() => handleDownload(report.id)}
                            disabled={report.status !== 'processed' || downloadingId === report.id}
                            color="primary"
                          >
                            {downloadingId === report.id ? <CircularProgress size={24} /> : <DownloadIcon />}
                          </IconButton>
                        </span>
                      </Tooltip>
                       <Tooltip title="Delete Report">
                          <span>
                            <IconButton
                              onClick={() => handleDeleteClick(report)}
                              color="error"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </span>
                       </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={totalCount}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      <ConfirmationDialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        onConfirm={handleConfirmDelete}
        title="Confirm Deletion"
        content={`Are you sure you want to delete the report for "${reportToDelete?.file_name}"? This action cannot be undone.`}
      />
    </Box>
  );
};

export default Reports;