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

  
  

// --- Search Related Types ---

  export interface PersonInfo {
    full_name: string;
    birth_date?: string;
    birth_date_iso?: string;
    address?: string;
    role?: string;
  }

  // Frontend representation of a company, aligning with backend CompanyInfo
  export interface Company {
    // Using backend field names directly for simplicity
    company_name: string;
    ico: string; // Keep as string since backend uses it as dict key
    file_reference?: string; // Maps to file_number/court display
    registration_date?: string;
    registration_date_iso?: string;
    person?: PersonInfo; // Included if searching by person
    // Frontend specific fields (optional)
    id: string; // Use ICO as the unique ID on the frontend
    description?: string; // You might want to add this if needed for display
    address?: string; // Add address if it's directly on CompanyInfo or derived
    court?: string; // Add court if derived from file_reference
  }

  // Parameters for the search API call
  export interface SearchParams {
    first_name?: string; // Changed from person_name
    last_name?: string;  // Added for person search
    company_name?: string;
    ico?: string; // Keep as string for consistency
  }

  // Structure of the response from /search/person and /search/company
  export interface CompanySearchResponse {
    companies: { [key: string]: Company }; // Dictionary keyed by ICO
    count: number;
  }

  // Structure for the valuation trigger response
  export interface ValuationResponse {
      status: string;
      report_id: string;
      message: string;
  }

  // --- Search Redux Slice State ---
  export interface SearchState {
    companies: Company[];
    isLoading: boolean;
    error: string | null;
    valuationStatus: 'idle' | 'pending' | 'success' | 'error';
    valuationReportId: string | null;
    valuationError: string | null;
    lastSearchType: 'person' | 'company' | 'ico' | null; // To know which search was last run
  }

    