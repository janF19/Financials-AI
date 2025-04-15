// src/services/api.ts
import axios, { AxiosRequestConfig } from 'axios';
import { LoginCredentials, RegisterCredentials, AuthResponse, Report, ReportFilterParams, DashboardSummary } from '../types';

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

export default api;