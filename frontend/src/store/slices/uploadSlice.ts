// src/store/slices/uploadSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { processService, reportService } from '../../services/api';
import { UploadState, Report } from '../../types';
import { toast } from 'react-toastify';
import { AxiosError } from 'axios';

// Async thunks
export const uploadPdfFile = createAsyncThunk(
  'upload/uploadPdfFile',
  async (file: File, { dispatch, rejectWithValue }) => {
    try {
      const response = await processService.uploadPdf(file, (progressEvent) => {
        const total = progressEvent.total || file.size;
        if (total > 0) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / total);
          dispatch(setProgress(percentCompleted));
        } else {
          dispatch(setProgress(0));
        }
      });
      
      dispatch(pollReportStatus(response.report_id));

      return response.report_id;
    } catch (error: unknown) {
      if (error instanceof AxiosError && error.response) {
        if (error.response.status === 429) {
          const message = error.response.data?.detail || 'You have reached your monthly upload limit.';
          return rejectWithValue(message);
        }
        const message = error.response.data?.detail || 'Failed to upload PDF file';
        return rejectWithValue(message);
      }
      return rejectWithValue('An unexpected error occurred during upload.');
    }
  }
);

export const pollReportStatus = createAsyncThunk<
  Report | null,
  string,
  { rejectValue: string }
>(
  'upload/pollReportStatus',
  async (reportId: string, { rejectWithValue }) => {
    try {
      let report: Report | null = null;
      let status = 'pending';
      let attempts = 0;
      const maxAttempts = 30;
      const pollInterval = 2000;

      console.log(`Polling status for report ${reportId}...`);

      while (status === 'pending' && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
        console.log(`Polling attempt ${attempts} for report ${reportId}`);
        try {
          report = await reportService.getReport(reportId);
          status = report.status;
          console.log(`Report ${reportId} status: ${status}`);
        } catch (pollError) {
          console.error(`Error fetching report status for ${reportId}:`, pollError);
          return rejectWithValue('Failed to check report status during polling.');
        }

        if (status !== 'pending') {
          console.log(`Polling finished for report ${reportId}. Final status: ${status}`);
          return report;
        }
      }

      if (attempts >= maxAttempts) {
        console.warn(`Polling timeout for report ${reportId}`);
        return rejectWithValue('Report processing is taking longer than expected. Please check back later.');
      }

      return report;
    } catch (error: unknown) {
      if (error instanceof AxiosError && error.response) {
        const message = error.response.data?.detail || 'Failed to start checking report status';
        return rejectWithValue(message);
      }
      return rejectWithValue('An unexpected error occurred while checking report status.');
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
    setProgress(state, action: PayloadAction<number>) {
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
      .addCase(uploadPdfFile.pending, (state) => {
        state.isUploading = true;
        state.progress = 0;
        state.reportId = null;
        state.error = null;
      })
      .addCase(uploadPdfFile.fulfilled, (state, action: PayloadAction<string>) => {
        state.reportId = action.payload;
        state.progress = 0;
      })
      .addCase(uploadPdfFile.rejected, (state, action) => {
        state.isUploading = false;
        state.error = action.payload as string;
        state.progress = 0;
        toast.error(action.payload as string);
      })
      
      .addCase(pollReportStatus.pending, (state) => {
        state.error = null;
      })
      .addCase(pollReportStatus.fulfilled, (state, action: PayloadAction<Report | null>) => {
        state.isUploading = false;
        if (action.payload) {
          if (action.payload.status === 'processed') {
            state.progress = 100;
            toast.success('Report processed successfully!');
          } else if (action.payload.status === 'failed') {
            state.error = action.payload.error_message || 'Processing failed';
            toast.error(`Processing failed: ${state.error}`);
          } else {
            state.error = `Report finished with unexpected status: ${action.payload.status}`;
            toast.warn(state.error);
          }
        } else {
          state.error = "Polling completed but no report data received.";
          toast.warn(state.error);
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