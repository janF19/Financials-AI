import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { infoService } from '../../services/api';
import { CompanyAllInfoResponse, CompanyInfoState } from '../../types/index.ts';
import { toast } from 'react-toastify';

// Async thunk for fetching company information
export const fetchCompanyInfo = createAsyncThunk(
  'companyInfo/fetchInfo',
  async (ico: string, { rejectWithValue }) => {
    try {
      // Validate ICO format (8 digits)
      if (!/^\d{8}$/.test(ico)) {
        toast.error('IČO must be an 8-digit number.');
        return rejectWithValue('Invalid IČO format. IČO must be an 8-digit number.');
      }
      const data = await infoService.getCompanyAllInfo(ico);
      if (!data || Object.keys(data).length === 0 || 
          (!data.justice_info && !data.dph_info && !data.dotace_info && !data.web_search_analysis)) {
        toast.warn(`No detailed information found for IČO: ${ico}. The company might not exist or data is unavailable.`);
        // Return a structured empty-like response or handle as needed
        // For now, we'll let it proceed and the UI can show "No data" messages per section
      }
      return data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || `Failed to fetch company information for IČO: ${ico}.`;
      toast.error(errorMessage);
      return rejectWithValue(errorMessage);
    }
  }
);

const initialState: CompanyInfoState = {
  data: null,
  isLoading: false,
  error: null,
  icoQuery: '',
};

const companyInfoSlice = createSlice({
  name: 'companyInfo',
  initialState,
  reducers: {
    clearCompanyInfo: (state) => {
      state.data = null;
      state.error = null;
      state.isLoading = false;
      // state.icoQuery = ''; // Optionally clear ICO query
    },
    setIcoQuery: (state, action: PayloadAction<string>) => {
      state.icoQuery = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCompanyInfo.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.data = null; // Clear previous data on new fetch
      })
      .addCase(fetchCompanyInfo.fulfilled, (state, action: PayloadAction<CompanyAllInfoResponse>) => {
        state.isLoading = false;
        state.data = action.payload;
      })
      .addCase(fetchCompanyInfo.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        state.data = null;
      });
  },
});

export const { clearCompanyInfo, setIcoQuery } = companyInfoSlice.actions;
export default companyInfoSlice.reducer; 