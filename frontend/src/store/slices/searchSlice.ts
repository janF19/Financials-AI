import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { searchService } from '../../services/api';
import { Company, SearchParams, SearchState, ValuationResponse } from '../../types/index.ts'; // Adjust path if needed

// Async thunk for fetching companies
export const fetchCompanies = createAsyncThunk(
  'search/fetchCompanies',
  async (params: SearchParams, { rejectWithValue }) => {
    try {
      const companies = await searchService.searchCompanies(params);
      // Determine search type based on params provided
      let type: SearchState['lastSearchType'] = null;
      if (params.first_name && params.last_name) type = 'person';
      else if (params.company_name) type = 'company';
      else if (params.ico) type = 'ico';
      return { companies, type };
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || error.message || 'Failed to fetch companies');
    }
  }
);

// Async thunk for triggering valuation
export const triggerValuation = createAsyncThunk(
  'search/triggerValuation',
  async (ico: string, { rejectWithValue }) => {
    try {
      const response = await searchService.valuateCompany(ico);
      return response; // Contains report_id, status, message
    } catch (error: any) {
      return rejectWithValue(error.response?.data?.detail || error.message || 'Failed to trigger valuation');
    }
  }
);

const initialState: SearchState = {
  companies: [],
  isLoading: false,
  error: null,
  valuationStatus: 'idle',
  valuationReportId: null,
  valuationError: null,
  lastSearchType: null,
};

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    clearSearchState: (state) => {
      state.companies = [];
      state.isLoading = false;
      state.error = null;
      state.lastSearchType = null;
      // Optionally reset valuation state too, or handle separately
      // state.valuationStatus = 'idle';
      // state.valuationReportId = null;
      // state.valuationError = null;
    },
    resetValuationStatus: (state) => {
        state.valuationStatus = 'idle';
        state.valuationReportId = null;
        state.valuationError = null;
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch Companies
      .addCase(fetchCompanies.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.companies = []; // Clear previous results on new search
        state.lastSearchType = null;
      })
      .addCase(fetchCompanies.fulfilled, (state, action: PayloadAction<{ companies: Company[], type: SearchState['lastSearchType'] }>) => {
        state.isLoading = false;
        state.companies = action.payload.companies;
        state.lastSearchType = action.payload.type;
        if (action.payload.companies.length === 0) {
            state.error = "No companies found matching your criteria.";
        }
      })
      .addCase(fetchCompanies.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      // Trigger Valuation
      .addCase(triggerValuation.pending, (state) => {
        state.valuationStatus = 'pending';
        state.valuationError = null;
        state.valuationReportId = null;
      })
      .addCase(triggerValuation.fulfilled, (state, action: PayloadAction<ValuationResponse>) => {
        state.valuationStatus = 'success'; // Indicates the trigger was successful
        state.valuationReportId = action.payload.report_id;
        // You might store the message from payload if needed
      })
      .addCase(triggerValuation.rejected, (state, action) => {
        state.valuationStatus = 'error';
        state.valuationError = action.payload as string;
      });
  },
});

export const { clearSearchState, resetValuationStatus } = searchSlice.actions;
export default searchSlice.reducer; 