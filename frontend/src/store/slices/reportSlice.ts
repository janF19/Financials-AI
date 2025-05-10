// src/store/slices/reportSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { reportService } from '../../services/api';
import { ReportsState, ReportFilterParams} from '../../types/index.ts';
import { toast } from 'react-toastify';

// Async thunks
export const fetchReports = createAsyncThunk(
  'reports/fetchReports',
  async (params: ReportFilterParams = {}, { rejectWithValue }) => {
    try {
      console.log('Calling reportService.getReports with params:', params);
      const data = await reportService.getReports(params);
      console.log('Response from reportService.getReports:', data);
      return data;
    } catch (error: any) {
      console.error('Error in fetchReports thunk:', error);
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch reports');
    }
  }
);

export const fetchReportById = createAsyncThunk(
  'reports/fetchReportById',
  async (id: string, { rejectWithValue }) => {
    try {
      const report = await reportService.getReport(id);
      return report;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch report');
    }
  }
);

export const downloadReport = createAsyncThunk(
  'reports/downloadReport',
  async (id: string, { rejectWithValue, dispatch }) => {
    try {
      console.log(`Starting download for report ${id}`);
      
      // Set a loading state that can be used to disable/enable the download button
      dispatch({ type: 'reports/setDownloadingId', payload: id });
      
      const response = await reportService.downloadReport(id);
      console.log(`Got response:`, response);
      
      // Check if the response is actually a blob
      if (!(response instanceof Blob)) {
        console.error('Response is not a Blob:', response);
        throw new Error('Invalid response format');
      }
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(response);
      console.log(`Created URL: ${url}`);
      
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report-${id}.docx`);
      document.body.appendChild(link);
      console.log('Clicking download link');
      link.click();
      
      // Clean up
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        link.remove();
        console.log('Download cleanup completed');
      }, 100);
      
      return id;
    } catch (error: any) {
      console.error('Download error:', error);
      return rejectWithValue(
        error.response?.data?.detail || error.message || 
        'Failed to download report. Please try again later.'
      );
    } finally {
      // Clear the downloading state
      dispatch({ type: 'reports/setDownloadingId', payload: null });
    }
  }
);

export const deleteReport = createAsyncThunk(
  'reports/deleteReport',
  async (id: string, { rejectWithValue }) => {
    try {
      await reportService.deleteReport(id);
      return id;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to delete report');
    }
  }
);

const initialState: ReportsState = {
  reports: [],
  currentReport: null,
  isLoading: false,
  error: null,
  totalCount: 0,
  downloadingId: null,
};

const reportSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    clearCurrentReport(state) {
      state.currentReport = null;
    },
    clearError(state) {
      state.error = null;
    },
    setDownloadingId(state, action) {
      state.downloadingId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch reports cases
      .addCase(fetchReports.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchReports.fulfilled, (state, action) => {
        state.isLoading = false;
        state.reports = action.payload.reports;
        state.totalCount = action.payload.total;
      })
      .addCase(fetchReports.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Fetch report by ID cases
      .addCase(fetchReportById.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchReportById.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentReport = action.payload;
      })
      .addCase(fetchReportById.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Download report cases
      .addCase(downloadReport.pending, () => {
        // We're now handling loading state via setDownloadingId
      })
      .addCase(downloadReport.fulfilled, (state) => {
        state.downloadingId = null;
        toast.success('Report downloaded successfully');
      })
      .addCase(downloadReport.rejected, (state, action) => {
        state.downloadingId = null;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Delete report cases
      .addCase(deleteReport.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(deleteReport.fulfilled, (state, action) => {
        state.isLoading = false;
        state.reports = state.reports.filter(report => report.id !== action.payload);
        toast.success('Report deleted successfully');
      })
      .addCase(deleteReport.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      });
  },
});

export const { clearCurrentReport, clearError, setDownloadingId } = reportSlice.actions;
export default reportSlice.reducer;