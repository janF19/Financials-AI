// src/types/index.ts

// Authentication types
export interface User {
    id: string;
    email: string;
    created_at: string;
  }
  
  export interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
  }
  
  export interface LoginCredentials {
    email: string;
    password: string;
  }
  
  export interface RegisterCredentials {
    email: string;
    password: string;
  }
  
  export interface AuthResponse {
    access_token: string;
    token_type: string;
  }
  
  // Report types
  export interface Report {
    id: string;
    file_name: string;
    status: 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
    download_url?: string;
    error_message?: string;
  }
  
  export interface ReportsState {
    reports: Report[];
    currentReport: Report | null;
    isLoading: boolean;
    error: string | null;
    totalCount: number;
  }
  
  export interface ReportFilterParams {
    status?: string;
    page?: number;
    limit?: number;
  }
  
  // Dashboard types
  export interface DashboardSummary {
    total_reports: number;
    processing_reports: number;
    completed_reports: number;
    failed_reports: number;
  }
  
  export interface DashboardState {
    summary: DashboardSummary;
    recentReports: Report[];
    isLoading: boolean;
    error: string | null;
  }
  
  // Process types
  export interface UploadState {
    isUploading: boolean;
    progress: number;
    reportId: string | null;
    error: string | null;
  }