// src/pages/Process.tsx
import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  LinearProgress,
  Alert,
  CircularProgress,
  Chip
} from '@mui/material';
import { CloudUpload as CloudUploadIcon, CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { uploadPdfFile, pollReportStatus, resetUpload } from '../store/slices/uploadSlice';
import { fetchReportById, clearCurrentReport, downloadReport } from '../store/slices/reportSlice'; // Import downloadReport

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB

const Process = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { isUploading, progress, reportId, error: uploadError } = useAppSelector((state) => state.upload);
  const { currentReport, error: reportError } = useAppSelector((state) => state.reports); // Use reportError

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  // Reset upload and report state when component unmounts or reportId changes
  useEffect(() => {
    return () => {
      dispatch(resetUpload());
      dispatch(clearCurrentReport()); // Clear report details on unmount
    };
  }, [dispatch]);

  // Poll for report status once we have a report ID
  useEffect(() => {
    if (reportId && isUploading) {
      dispatch(pollReportStatus(reportId));
    }
  }, [dispatch, reportId, isUploading]);

  // Fetch report details when polling is complete (isUploading becomes false but reportId exists)
  useEffect(() => {
    if (reportId && !isUploading) {
      dispatch(fetchReportById(reportId));
    }
  }, [dispatch, reportId, isUploading]);

  const validateFile = (selectedFile: File): boolean => {
    if (!selectedFile) {
      setFileError('Please select a file');
      return false;
    }

    if (!selectedFile.type.includes('pdf')) {
      setFileError('Only PDF files are allowed');
      return false;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setFileError(`File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`);
      return false;
    }

    setFileError(null);
    return true;
  };

  const handleFileDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
      }
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
      } else {
        setFile(null); // Clear file if validation fails
        e.target.value = ''; // Reset file input
      }
    }
  };

  const handleUpload = () => {
    if (file && validateFile(file)) {
      dispatch(resetUpload()); // Reset state before new upload
      dispatch(clearCurrentReport()); // Clear previous report details
      dispatch(uploadPdfFile(file));
    }
  };

  const handleReset = () => {
    setFile(null);
    setFileError(null);
    dispatch(resetUpload());
    dispatch(clearCurrentReport());
    // Also reset the file input visually if possible
    const fileInput = document.getElementById('fileInput') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleViewReports = () => {
    navigate(`/reports`);
  };

  const handleDownload = () => {
    if (currentReport?.id && currentReport.status === 'processed') {
      dispatch(downloadReport(currentReport.id));
    }
  };

  // Determine combined error state
  const displayError = uploadError || reportError;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Process Financial Document
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="body1" sx={{ mb: 2 }}>
          Upload a PDF financial document (max 5MB) to process. The system will analyze the document and generate a valuation report.
        </Typography>

        {/* File Input Area - Shown when not uploading and no final report displayed yet */}
        {!isUploading && !currentReport && (
          <>
            <Box
              sx={{
                border: dragActive ? '2px dashed #2196f3' : `2px dashed ${fileError ? '#d32f2f' : '#cccccc'}`, // Highlight red on error
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                bgcolor: dragActive ? 'rgba(33, 150, 243, 0.04)' : 'background.paper',
                cursor: 'pointer',
                mb: 2,
              }}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleFileDrop}
              onClick={() => document.getElementById('fileInput')?.click()}
            >
              <input
                type="file"
                id="fileInput"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={handleFileChange}
                disabled={isUploading}
              />
              <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6">
                {file ? file.name : 'Drag & Drop your PDF here or click to browse'}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                PDF files only, 5MB maximum
              </Typography>
            </Box>

            {fileError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {fileError}
              </Alert>
            )}

            {displayError && !isUploading && ( // Show upload/report fetch errors here too
              <Alert severity="error" sx={{ mb: 2 }}>
                {displayError}
              </Alert>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 2 }}>
              <Button
                variant="contained"
                onClick={handleUpload}
                disabled={!file || !!fileError || isUploading}
              >
                Upload & Process
              </Button>
              {file && (
                <Button variant="outlined" onClick={handleReset} disabled={isUploading}>
                  Clear Selection
                </Button>
              )}
            </Box>
          </>
        )}

        {/* Uploading/Processing State */}
        {isUploading && (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            <Typography variant="body1" sx={{ mb: 2 }}>
              {progress < 100 ? 'Uploading file...' : 'Processing document...'}
            </Typography>
            <LinearProgress
              variant={progress < 100 ? "determinate" : "indeterminate"} // Use indeterminate while processing
              value={progress < 100 ? progress : undefined}
              sx={{ height: 10, borderRadius: 5, mb: 2 }}
            />
            <Typography variant="body2" color="textSecondary">
              {progress < 100
                ? `Upload progress: ${progress}%`
                : 'File uploaded. Analyzing the document. This may take a few minutes...'}
            </Typography>
            <CircularProgress sx={{ mt: 3 }} />
          </Box>
        )}

        {/* Display Upload/Polling Error - Shown only if an error occurred during the process */}
         {displayError && isUploading && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {displayError}
          </Alert>
        )}

        {/* Process Complete State */}
        {currentReport && !isUploading && (
          <Box sx={{ textAlign: 'center', py: 2 }}>
            {currentReport.status === 'processed' && (
              <Box>
                <CheckCircle color="success" sx={{ fontSize: 48, mb: 1 }} />
                <Typography variant="h6" color="success.main">Processing Successful!</Typography>
                <Typography variant="body1" sx={{ mt: 1, mb: 2 }}>
                  Your report for '{currentReport.file_name}' is ready.
                </Typography>
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
                  <Button variant="contained" color="primary" onClick={handleDownload}>
                    Download Report
                  </Button>
                   <Button variant="outlined" onClick={handleReset}>
                    Upload Another File
                  </Button>
                  <Button variant="text" onClick={handleViewReports}>
                    View All Reports
                  </Button>
                </Box>
              </Box>
            )}
            {currentReport.status === 'failed' && (
              <Box>
                <ErrorIcon color="error" sx={{ fontSize: 48, mb: 1 }} />
                <Typography variant="h6" color="error.main">Processing Failed</Typography>
                <Typography variant="body1" sx={{ mt: 1 }}>
                  Processing failed for '{currentReport.file_name}'.
                </Typography>
                {currentReport.error_message && (
                  <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>
                    Reason: {currentReport.error_message}
                  </Alert>
                )}
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
                  <Button variant="outlined" onClick={handleReset}>
                    Try Uploading Again
                  </Button>
                   <Button variant="text" onClick={handleViewReports}>
                    View All Reports
                  </Button>
                </Box>
              </Box>
            )}
            {/* Handle unexpected status just in case */}
            {currentReport.status !== 'processed' && currentReport.status !== 'failed' && (
                 <Box>
                    <Typography variant="h6">Processing Status: <Chip label={currentReport.status} /></Typography>
                     <Typography variant="body1" sx={{ mt: 1, mb: 2 }}>
                       File: '{currentReport.file_name}'. The status is unexpected.
                     </Typography>
                      <Button variant="outlined" onClick={handleReset}>
                        Upload Another File
                      </Button>
                 </Box>
            )}
          </Box>
        )}

      </Paper>
    </Box>
  );
};

export default Process;