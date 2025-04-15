// src/store/slices/uploadSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { processService, reportService } from '../../services/api';
import { UploadState } from '../../types';
import { toast } from 'react-toastify';

// Async thunks
export const uploadPdfFile = createAsyncThunk(
  'upload/uploadPdfFile',
  async (file: File, { dispatch, rejectWithValue }) => {
    try {
      const response = await processService.uploadPdf(file, (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        dispatch(setProgress(percentCompleted));
      });
      
      return response.report_id;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to upload PDF file');
    }
  }
);

export const pollReportStatus = createAsyncThunk(
  'upload/pollReportStatus',
  async (reportId: string, { dispatch, rejectWithValue }) => {
    try {
      let status = 'processing';
      let attempts = 0;
      const maxAttempts = 30; // Max polling attempts
      
      while (status === 'processing' && attempts < maxAttempts) {
        const report = await reportService.getReport(reportId);
        status = report.status;
        
        if (status !== 'processing') {
          return report;
        }
        
        // Wait 2 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
      }
      
      if (attempts >= maxAttempts) {
        return rejectWithValue('Report processing timeout');
      }
      
      return null;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to check report status');
    }
  }
);

const initialState: UploadState = {
  isUploading: false,
  progress: 0,
  reportId: null,
  error: null,
};

const uploadSlice = createSlice({
  name: 'upload',
  initialState,
  reducers: {
    setProgress(state, action) {
      state.progress = action.payload;
    },
    resetUpload(state) {
      state.isUploading = false;
      state.progress = 0;
      state.reportId = null;
      state.error = null;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Upload PDF cases
      .addCase(uploadPdfFile.pending, (state) => {
        state.isUploading = true;
        state.progress = 0;
        state.error = null;
      })
      .addCase(uploadPdfFile.fulfilled, (state, action) => {
        state.reportId = action.payload;
        // Keep isUploading true while we poll
      })
      .addCase(uploadPdfFile.rejected, (state, action) => {
        state.isUploading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Poll report status cases
      .addCase(pollReportStatus.pending, (state) => {
        // Continue showing upload progress
      })
      .addCase(pollReportStatus.fulfilled, (state, action) => {
        state.isUploading = false;
        state.progress = 100;
        
        if (action.payload) {
          if (action.payload.status === 'completed') {
            toast.success('Report processed successfully!');
          } else if (action.payload.status === 'failed') {
            state.error = action.payload.error_message || 'Processing failed';
            toast.error(`Processing failed: ${state.error}`);
          }
        }
      })
      .addCase(pollReportStatus.rejected, (state, action) => {
        state.isUploading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      });
  },
});

export const { setProgress, resetUpload, clearError } = uploadSlice.actions;
export default uploadSlice.reducer;