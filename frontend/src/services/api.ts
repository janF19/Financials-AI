// src/services/api.ts
import axios, { AxiosRequestConfig } from 'axios';
import { LoginCredentials, RegisterCredentials, AuthResponse, Report, ReportFilterParams, DashboardSummary, Company, SearchParams, CompanySearchResponse, ValuationResponse, ChatRequestAPI, ChatResponseAPI, FileUploadResponseAPI, CompanyAllInfoResponse } from '../types/index.ts';

const API_URL = import.meta.env.VITE_API_URL;

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auth services
export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await api.post('/auth/token', new URLSearchParams({
      username: credentials.email,
      password: credentials.password,
    }), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  register: async (credentials: RegisterCredentials): Promise<void> => {
    await api.post('/auth/register', credentials);
  },

  getProfile: async (): Promise<any> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  updateProfile: async (data: any): Promise<any> => {
    const response = await api.put('/auth/me', data);
    return response.data;
  },
};

// Reports services
export const reportService = {
  getReports: async (params?: ReportFilterParams): Promise<{ reports: Report[], total: number }> => {
    console.log('API call: getReports with params:', params);
    try {
      const response = await api.get('/reports/', { params });
      console.log('API response for getReports:', response.data);
      return response.data;
    } catch (error) {
      console.error('API error in getReports:', error);
      throw error;
    }
  },

  getReport: async (id: string): Promise<Report> => {
    const response = await api.get(`/reports/${id}`);
    return response.data;
  },

  downloadReport: async (id: string): Promise<Blob> => {
    console.log(`Making API call to ${API_URL}/reports/${id}/download`);
    const response = await api.get(`/reports/${id}/download`, {
      responseType: 'blob',
    });
    console.log("Download response:", response);
    return response.data;
  },

  deleteReport: async (id: string): Promise<void> => {
    await api.delete(`/reports/${id}`);
  },
};

// Financial processing service
export const processService = {
  uploadPdf: async (file: File, onUploadProgress?: (progressEvent: any) => void): Promise<{ report_id: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    };

    const response = await api.post('/financials/process', formData, config);
    return response.data;
  },
};

// Dashboard service
export const dashboardService = {
  getDashboardData: async (): Promise<any> => {
    const response = await api.get('/dashboard/');
    return response.data;
  },

  getReportsSummary: async (): Promise<DashboardSummary> => {
    const response = await api.get('/dashboard/reports-summary');
    return response.data;
  },
};

// Search service
export const searchService = {
  searchCompanies: async (params: SearchParams): Promise<Company[]> => {
    let endpoint = '/search'; // Base path
    let requestParams: any = {};
    let searchType: 'person' | 'company' | 'ico' | null = null;

    // Determine endpoint and parameters based on input
    if (params.first_name && params.last_name) {
      endpoint += '/person';
      requestParams = { first_name: params.first_name, last_name: params.last_name };
      searchType = 'person';
    } else if (params.company_name) {
      endpoint += '/company';
      requestParams = { company_name: params.company_name };
      searchType = 'company';
    } else if (params.ico) {
      endpoint += '/ico';
      // Ensure ICO is sent as a number if the backend expects int
      requestParams = { ico: parseInt(params.ico, 10) };
      searchType = 'ico';
    } else {
      // Should be handled by frontend validation, but good to have a fallback
      console.error('No valid search parameters provided.');
      return [];
    }

    console.log(`API call: searchCompanies to ${endpoint} with params:`, requestParams);

    try {
      const response = await api.get(endpoint, { params: requestParams });
      console.log('API response for searchCompanies:', response.data);

      let companiesArray: Company[] = [];

      if (searchType === 'person' || searchType === 'company') {
        // Response format: { companies: { ico: CompanyInfo }, count: number }
        const data = response.data as CompanySearchResponse;
        companiesArray = Object.entries(data.companies).map(([ico, companyData]) => ({
          ...companyData,
          id: ico, // Use ICO as the frontend ID
          // You might need to parse file_reference here if needed
          // e.g., file_number: companyData.file_reference?.split(' vedená u ')[0],
          //       court: companyData.file_reference?.split(' vedená u ')[1],
        }));
      } else if (searchType === 'ico') {
        // Response format: CompanyInfo
        const companyData = response.data as Company;
        if (companyData && companyData.ico) {
           companiesArray = [{
             ...companyData,
             id: companyData.ico, // Use ICO as the frontend ID
             // Parse file_reference if needed
           }];
        } else {
            console.warn("Received empty or invalid data for ICO search");
        }
      }

      return companiesArray;

    } catch (error) {
      console.error(`API error in searchCompanies (${searchType}):`, error);
      throw error; // Re-throw to be caught by the component/thunk
    }
  },

  // Function to trigger valuation
  valuateCompany: async (ico: string): Promise<ValuationResponse> => {
    const endpoint = '/search/valuate';
    // Ensure ICO is sent as a number if the backend expects int
    const params = { ico: parseInt(ico, 10) };
    console.log(`API call: valuateCompany to ${endpoint} with ICO:`, params.ico);
    try {
        // Use POST method as defined in backend
        const response = await api.post(endpoint, null, { params }); // Send ICO as query param
        console.log('API response for valuateCompany:', response.data);
        return response.data as ValuationResponse;
    } catch (error) {
        console.error('API error in valuateCompany:', error);
        throw error;
    }
  }
};

// Info service (for the new Company Information page)
export const infoService = {
  getCompanyAllInfo: async (ico: string): Promise<CompanyAllInfoResponse> => {
    const endpoint = `/info/${ico}`;
    console.log(`API call: getCompanyAllInfo to ${endpoint}`);
    try {
      const response = await api.get(endpoint);
      console.log('API response for getCompanyAllInfo:', response.data);
      return response.data as CompanyAllInfoResponse;
    } catch (error) {
      console.error(`API error in getCompanyAllInfo for ICO ${ico}:`, error);
      throw error; // Re-throw to be caught by the thunk
    }
  }
};

// Chat service
export const chatService = {
  sendChatMessage: async (request: ChatRequestAPI): Promise<ChatResponseAPI> => {
    const response = await api.post('/chat/chat', request);
    return response.data;
  },

  uploadPdfForChat: async (file: File, onUploadProgress?: (progressEvent: any) => void): Promise<FileUploadResponseAPI> => {
    const formData = new FormData();
    formData.append('file', file);

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    };
    // Assuming the backend endpoint for chat PDF upload is /chat/upload-pdf
    const response = await api.post('/chat/upload-pdf', formData, config);
    return response.data;
  }
};

export default api;