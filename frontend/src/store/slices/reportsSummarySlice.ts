import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { dashboardService } from '../../services/api'; // This service might also be a candidate for renaming later if it becomes confusing
import { Report } from '../../types/index'; // Assuming Report type is used for recentReports
import { toast } from 'react-toastify';

// Define a more specific state type name
export interface ReportsSummaryState {
  summary: {
    total_reports: number;
    processing_reports: number;
    completed_reports: number;
    failed_reports: number;
  };
  recentReports: Report[]; // Use the existing Report type if applicable
  isLoading: boolean;
  error: string | null;
}

// Async thunks
// Renamed from fetchDashboardData
export const fetchRecentReportsData = createAsyncThunk(
  'reportsSummary/fetchRecentReportsData', // Changed action type prefix
  async (_, { rejectWithValue }) => {
    try {
      // This endpoint might still be called 'dashboardData' on the backend,
      // but its role here is to fetch data for the reports summary section.
      const data = await dashboardService.getDashboardData();
      return data; // Expecting { recent_reports: Report[] }
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch recent reports data');
    }
  }
);

export const fetchReportsSummary = createAsyncThunk(
  'reportsSummary/fetchReportsSummary', // Changed action type prefix
  async (_, { rejectWithValue }) => {
    try {
      const summary = await dashboardService.getReportsSummary();
      return summary;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch reports summary');
    }
  }
);

const initialState: ReportsSummaryState = {
  summary: {
    total_reports: 0,
    processing_reports: 0,
    completed_reports: 0,
    failed_reports: 0,
  },
  recentReports: [],
  isLoading: false,
  error: null,
};

const reportsSummarySlice = createSlice({
  name: 'reportsSummary', // Renamed slice
  initialState,
  reducers: {
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch recent reports data cases
      .addCase(fetchRecentReportsData.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchRecentReportsData.fulfilled, (state, action) => {
        state.isLoading = false;
        // Assuming the payload from getDashboardData has a recent_reports field
        state.recentReports = action.payload.recent_reports || [];
      })
      .addCase(fetchRecentReportsData.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Fetch reports summary cases
      .addCase(fetchReportsSummary.pending, (state) => {
        // Potentially set isLoading true only if not already loading from fetchRecentReportsData
        // or manage separate loading flags if they can load independently and concurrently.
        // For simplicity, one isLoading flag is often used if they are fetched close together.
        state.isLoading = true; 
      })
      .addCase(fetchReportsSummary.fulfilled, (state, action) => {
        state.isLoading = false;
        state.summary = action.payload;
      })
      .addCase(fetchReportsSummary.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      });
  },
});

export const { clearError } = reportsSummarySlice.actions;
export default reportsSummarySlice.reducer; 