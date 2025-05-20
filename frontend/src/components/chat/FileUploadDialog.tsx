import React, { useState, useRef } from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Typography,
  Box,
  CircularProgress,
  Alert
} from '@mui/material';
import { UploadFile as UploadFileIcon, CheckCircleOutline as CheckCircleIcon} from '@mui/icons-material';

interface FileUploadDialogProps {
  open: boolean;
  onClose: () => void;
  onFileUpload: (file: File) => Promise<void>; // The function from useChat
  isUploading: boolean; // From useChat
  uploadedFileDisplayName?: string | null; // From useChat (file.display_name)
}

const FileUploadDialog: React.FC<FileUploadDialogProps> = ({
  open,
  onClose,
  onFileUpload,
  isUploading,
  uploadedFileDisplayName,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type === 'application/pdf') {
        if (file.size <= 5 * 1024 * 1024) { // 5MB limit, adjust as needed
          setSelectedFile(file);
          setFileError(null);
        } else {
          setFileError('File is too large. Maximum size is 5MB.');
          setSelectedFile(null);
        }
      } else {
        setFileError('Invalid file type. Only PDF files are allowed.');
        setSelectedFile(null);
      }
    }
  };

  const handleTriggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleConfirmUpload = async () => {
    if (selectedFile) {
      await onFileUpload(selectedFile);
      // onClose will be called by ChatInterface if upload is successful or if user closes it
      // Reset local state for next time
      // setSelectedFile(null); // Keep selected file to show its name until dialog is closed
    }
  };
  
  const handleDialogClose = () => {
    setSelectedFile(null);
    setFileError(null);
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleDialogClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload PDF Document</DialogTitle>
      <DialogContent>
        {!selectedFile && !uploadedFileDisplayName && (
          <DialogContentText sx={{ mb: 2 }}>
            Select a PDF file to attach to your message. Max file size: 5MB.
          </DialogContentText>
        )}
        
        {fileError && <Alert severity="error" sx={{ mb: 2 }}>{fileError}</Alert>}

        {uploadedFileDisplayName && !isUploading && (
           <Box sx={{ display: 'flex', alignItems: 'center', p: 2, backgroundColor: 'success.light', borderRadius: 1, mb:2 }}>
             <CheckCircleIcon color="success" sx={{ mr: 1 }} />
             <Typography>File "<strong>{uploadedFileDisplayName}</strong>" is ready to be sent with your next message.</Typography>
           </Box>
        )}

        <input
          type="file"
          accept=".pdf"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<UploadFileIcon />}
            onClick={handleTriggerFileInput}
            disabled={isUploading || !!uploadedFileDisplayName}
          >
            {selectedFile ? `Change File: ${selectedFile.name}` : 'Choose PDF File'}
          </Button>
          {selectedFile && !uploadedFileDisplayName && (
            <Typography variant="body2" color="text.secondary">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
            </Typography>
          )}
        </Box>

      </DialogContent>
      <DialogActions sx={{p:2}}>
        <Button onClick={handleDialogClose} color="inherit" disabled={isUploading}>
          {uploadedFileDisplayName ? 'Close' : 'Cancel'}
        </Button>
        <Button
          onClick={handleConfirmUpload}
          variant="contained"
          color="primary"
          disabled={!selectedFile || isUploading || !!uploadedFileDisplayName}
          startIcon={isUploading ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {isUploading ? 'Uploading...' : 'Upload and Attach'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FileUploadDialog; 