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
    status: 'pending' | 'processed' | 'failed';
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

  
  export interface ReportsState {
    // ... existing properties
    downloadingId: string | null;
  }



/////////////////////////////////




// Chat Types
export interface ChatMessageAPI { // For API communication
  role: 'user' | 'model'; // Gemini uses 'user' and 'model'
  content: string;
}

export interface ChatMessageUI { // For UI display
  id: string;
  role: 'user' | 'assistant'; // UI might prefer 'assistant' for model
  content: string;
  timestamp: Date;
  fileDisplayName?: string; // To show the name of the file sent with the user message
}

export interface ChatRequestAPI {
  message: string;
  file_uri?: string | null; // URI from the /upload-pdf endpoint
  history?: ChatMessageAPI[];
}

export interface ChatResponseAPI {
  response: string; // The text response from the model
}

export interface FileUploadResponseAPI { // Response from /chat/upload-pdf
  file_uri: string;
  display_name: string;
}

export interface PromptTemplate {
  id: string;
  title: string;
  description: string;
  prompt: string;
  tags?: string[]; // Optional: for categorizing templates
}

// Add this to your existing types or ensure they are covered
// This is a placeholder, adjust according to your actual store structure if different
// export interface RootState { // This is now generated in store/index.ts
//   auth: {
// ...
// existing code...
// --- Company Info (Research) Types ---

export interface JusticeInfoSidlo {
  adresa_kompletni?: string | null;
}

export interface JusticeInfoStatutarniOrganClen {
  role?: string;
  jmeno_prijmeni?: string;
  datum_narozeni?: string;
  // Add other fields if present, e.g., address
}

export interface JusticeInfoStatutarniOrgan {
  clenove?: JusticeInfoStatutarniOrganClen[];
  pocet_clenu?: number | string; // string if it can be "neuvedeno"
  zpusob_jednani?: string;
  // It can also be a simple string if no structured data
}

export interface JusticeInfoJedinyAkcionar {
  nazev?: string | null;
  ic?: string | null;
  adresa?: string | null;
}

export interface JusticeInfoAkcieItem {
  popis_akcie?: string | null;
  podminky_prevodu?: string | null;
  // Add other potential fields if they exist
}

export interface JusticeInfo {
  obchodni_firma?: string | null;
  sídlo?: JusticeInfoSidlo | null;
  identifikacni_cislo?: string | null;
  pravni_forma?: string | null;
  datum_vzniku_a_zapisu?: string | null;
  spisova_znacka?: string | null;
  predmet_podnikani?: string[];
  statutarni_organ_predstavenstvo?: JusticeInfoStatutarniOrgan | string | null; // Can be complex object or string
  dozorci_rada?: any; // Define more strictly if structure is known
  prokura?: any; // Define more strictly if structure is known
  jediny_akcionar?: JusticeInfoJedinyAkcionar | string | null; // Updated type
  akcie?: (JusticeInfoAkcieItem | string)[]; // Updated type, can be array of objects or strings
  zakladni_kapital?: string | null;
  splaceno?: string | null;
  ostatni_skutecnosti?: string[];
}

export interface DphInfo {
  nespolehlivy_platce?: string | null; // e.g., "NE", "ANO", or null
  registrace_od_data?: string | null;
}

export interface DotaceInfo {
  uvolnena?: number | null;
}

export interface WebSearchAnalysis {
  name?: string | null;
  summary?: string[] | null;
}

export interface CompanyAllInfoResponse {
  justice_info?: JusticeInfo | null;
  dph_info?: DphInfo | null;
  dotace_info?: DotaceInfo | null;
  web_search_analysis?: WebSearchAnalysis | null;
}

export interface CompanyInfoState {
  data: CompanyAllInfoResponse | null;
  isLoading: boolean;
  error: string | null;
  icoQuery: string; // To store the last searched ICO for confirmation
}

// --- Chat Redux Slice State ---
export interface ChatState {
  messages: ChatMessageUI[];
  isLoading: boolean; // For message sending
  error: string | null; // For message sending errors
  currentFileUri: string | null; // URI of the uploaded file for the current/next message
  currentFileDisplayName: string | null; // Display name of the uploaded file
  isFileContextApplied: boolean; // True if the current file has been used in a sent message
  isUploading: boolean; // For file upload
  uploadError: string | null; // For file upload errors
  uploadProgress: number; // File upload progress (0-100)
  inputPrompt: string; // Stores prompt from template to be used in input
}





