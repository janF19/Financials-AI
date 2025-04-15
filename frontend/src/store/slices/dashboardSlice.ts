// src/store/slices/dashboardSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { dashboardService } from '../../services/api';
import { DashboardState } from '../../types';
import { toast } from 'react-toastify';

// Async thunks
export const fetchDashboardData = createAsyncThunk(
  'dashboard/fetchDashboardData',
  async (_, { rejectWithValue }) => {
    try {
      const dashboardData = await dashboardService.getDashboardData();
      return dashboardData;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch dashboard data');
    }
  }
);

export const fetchReportsSummary = createAsyncThunk(
  'dashboard/fetchReportsSummary',
  async (_, { rejectWithValue }) => {
    try {
      const summary = await dashboardService.getReportsSummary();
      return summary;
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch reports summary');
    }
  }
);

const initialState: DashboardState = {
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

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch dashboard data cases
      .addCase(fetchDashboardData.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDashboardData.fulfilled, (state, action) => {
        state.isLoading = false;
        state.recentReports = action.payload.recent_reports || [];
      })
      .addCase(fetchDashboardData.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        toast.error(action.payload as string);
      })
      
      // Fetch reports summary cases
      .addCase(fetchReportsSummary.pending, (state) => {
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

export const { clearError } = dashboardSlice.actions;
export default dashboardSlice.reducer;