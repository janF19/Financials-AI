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
  Button
} from '@mui/material';
import { Download as DownloadIcon, Delete as DeleteIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { fetchReports, downloadReport, deleteReport } from '../store/slices/reportSlice';
import { Report } from '../types';

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

const Reports = () => {
  const dispatch = useAppDispatch();
  const { reports = [], totalCount = 0, isLoading, error } = useAppSelector((state) => state.reports);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>(''); // 'all', 'processing', 'completed', 'failed'
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
      .then(data => {
        console.log('Reports fetch successful:', data);
      })
      .catch(err => {
        console.error('Reports fetch error:', err);
      });
  }

  useEffect(() => {
    fetchReportsData();
  }, [dispatch, page, rowsPerPage, statusFilter]);

  useEffect(() => {
    // When reports are loaded
    console.log("Reports with statuses:", reports.map((r: Report) => ({ id: r.id, status: r.status })));
  }, [reports]);

  const handleChangePage = (event: unknown, newPage: number) => {
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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        My Reports
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
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
             <MenuItem value="processing">Processing</MenuItem>
             <MenuItem value="completed">Completed</MenuItem>
             <MenuItem value="failed">Failed</MenuItem>
           </Select>
         </FormControl>
          <Tooltip title="Refresh List">
              <IconButton onClick={fetchReportsData} disabled={isLoading}>
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
              {isLoading && (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              )}
              {!isLoading && reports.length === 0 && (
                 <TableRow>
                   <TableCell colSpan={5} align="center">
                      No reports found. {statusFilter !== 'all' ? 'Try adjusting the filter.' : 'Upload a document to get started.'}
                   </TableCell>
                 </TableRow>
              )}
              {!isLoading &&
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
                      <Tooltip title="Download Report">
                        <span>
                          <IconButton
                            onClick={() => handleDownload(report.id)}
                            disabled={report.status !== 'completed'}
                            color="primary"
                          >
                            <DownloadIcon />
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