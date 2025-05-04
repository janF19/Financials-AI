import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Card,
  CardContent,
  CardActions,
  Grid,
  CircularProgress,
  Alert,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Snackbar,
  Divider
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { useAppDispatch, useAppSelector } from '../hooks/redux'; // Use Redux hooks
import { fetchCompanies, triggerValuation, resetValuationStatus } from '../store/slices/searchSlice'; // Import actions/thunks
import { Company, SearchParams } from '../types/index.ts'; // Ensure path is correct
import { toast } from 'react-toastify'; // For notifications

const SearchPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const {
    companies: searchResults, // Rename from state for clarity
    isLoading,
    error,
    valuationStatus,
    valuationReportId,
    valuationError,
    lastSearchType // Get last search type from state
  } = useAppSelector((state) => state.search);

  // Local state for form inputs
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [ico, setIco] = useState('');

  // Local state for dialog
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

  // State for Snackbar notification
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // Effect to show notifications based on valuation status
  useEffect(() => {
    if (valuationStatus === 'success') {
      toast.success(`Valuation process started successfully! Report ID: ${valuationReportId}`);
      dispatch(resetValuationStatus()); // Reset status after showing toast
    } else if (valuationStatus === 'error') {
      toast.error(`Valuation failed: ${valuationError}`);
      dispatch(resetValuationStatus()); // Reset status after showing toast
    }
  }, [valuationStatus, valuationReportId, valuationError, dispatch]);

  const handleSearch = (type: 'person' | 'company' | 'ico') => {
    let params: SearchParams = {};
    let canSearch = false;

    if (type === 'person' && firstName && lastName) {
      params = { first_name: firstName, last_name: lastName };
      canSearch = true;
    } else if (type === 'company' && companyName) {
      params = { company_name: companyName };
      canSearch = true;
    } else if (type === 'ico' && ico) {
      params = { ico: ico };
      canSearch = true;
    }

    if (canSearch) {
      dispatch(fetchCompanies(params));
    } else {
        // Basic validation feedback (could use form helper text)
        toast.warn('Please fill in the required fields for the search.');
    }
  };

  const handleValuationSelect = (company: Company) => {
    setSelectedCompany(company);
    setIsDialogOpen(true);
  };

  const handleConfirmValuation = () => {
    if (selectedCompany) {
      dispatch(triggerValuation(selectedCompany.ico)); // Dispatch valuation thunk
      setIsDialogOpen(false);
      setSelectedCompany(null);
      // Optionally clear search results or disable buttons while valuation is pending
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setSelectedCompany(null);
  };

  // Helper to parse file reference
  const parseFileReference = (fileRef?: string): { fileNumber: string, court: string } => {
      if (!fileRef) return { fileNumber: '', court: '' };
      const parts = fileRef.split(' vedená u ');
      return {
          fileNumber: parts[0] || '',
          court: parts[1] || ''
      };
  };

  // Helper component for consistent label-value display (optional, can be inlined)
  const LabelValue = ({ label, value, isBoldValue = false }: { label: string, value?: string | null, isBoldValue?: boolean }) => {
    if (!value) return null; // Don't render if value is empty or null
    return (
      <Box sx={{ display: 'flex', mb: 0.5, alignItems: 'baseline' }}>
        <Typography variant="body2" color="text.secondary" sx={{ width: '130px', flexShrink: 0, pr: 1 }}> {/* Adjust width as needed */}
          {label}:
        </Typography>
        <Typography variant="body2" fontWeight={isBoldValue ? 'bold' : 'regular'}>
          {value}
        </Typography>
      </Box>
    );
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search Companies
      </Typography>
      <Typography variant="subtitle1" gutterBottom>
        Search with one of the methods to find the company you want to valuate.
      </Typography>

      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={3}>
          {/* Search by Person Name */}
          <Grid xs={12}>
            <Typography variant="body1" gutterBottom>
              Search company based on participation by person name:
            </Typography>
            <Grid container spacing={2} alignItems="center">
                 <Grid xs={12} sm={5}>
                     <TextField
                        fullWidth
                        label="First Name"
                        variant="outlined"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        disabled={isLoading}
                        size="small"
                     />
                 </Grid>
                 <Grid xs={12} sm={5}>
                     <TextField
                        fullWidth
                        label="Last Name"
                        variant="outlined"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        disabled={isLoading}
                        size="small"
                     />
                 </Grid>
                 <Grid xs={12} sm={2}>
                    <Button
                        fullWidth
                        variant="contained"
                        onClick={() => handleSearch('person')}
                        disabled={isLoading || !firstName || !lastName || valuationStatus === 'pending'}
                        startIcon={<SearchIcon />}
                    >
                        Search
                    </Button>
                 </Grid>
            </Grid>
          </Grid>

          {/* Search by Company Name */}
          <Grid xs={12}>
            <Typography variant="body1" gutterBottom>
              Search company based on name:
            </Typography>
             <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Enter name of company"
                variant="outlined"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                disabled={isLoading || valuationStatus === 'pending'}
                size="small"
              />
              <Button
                variant="contained"
                onClick={() => handleSearch('company')}
                disabled={isLoading || !companyName || valuationStatus === 'pending'}
                startIcon={<SearchIcon />}
              >
                Search
              </Button>
            </Box>
          </Grid>

          {/* Search by ICO */}
          <Grid item xs={12}>
            <Typography variant="body1" gutterBottom>
              Search company based on IČO:
            </Typography>
             <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Enter IČO"
                variant="outlined"
                value={ico}
                onChange={(e) => setIco(e.target.value)}
                disabled={isLoading || valuationStatus === 'pending'}
                size="small"
                type="number" // Basic type validation
              />
              <Button
                variant="contained"
                onClick={() => handleSearch('ico')}
                disabled={isLoading || !ico || valuationStatus === 'pending'}
                startIcon={<SearchIcon />}
              >
                Search
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Loading Indicator */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Searching...</Typography>
        </Box>
      )}

       {/* Valuation Pending Indicator */}
       {valuationStatus === 'pending' && (
         <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
           <CircularProgress color="secondary" />
           <Typography sx={{ ml: 2 }} color="text.secondary">Starting valuation process...</Typography>
         </Box>
       )}

      {/* Error Message */}
      {error && !isLoading && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}

      {/* Search Results */}
      {!isLoading && !error && lastSearchType && searchResults.length > 0 && (
        <Box sx={{ mt: 4 }}> {/* Add margin top to separate from forms */}
          {/* Results Header */}
          <Paper elevation={1} sx={{ bgcolor: 'success.dark', color: 'white', p: 2, borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>
             <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">
                    Search Results: {searchResults.length} compan{searchResults.length === 1 ? 'y' : 'ies'} found
                </Typography>
                <Typography variant="caption">Data retrieved {new Date().toLocaleTimeString()}</Typography>
             </Box>
          </Paper>

          {/* Results List - Remove the outer Grid container */}
          <Box sx={{ border: '1px solid', borderColor: 'divider', borderTop: 'none' }}> {/* Add border around the list */}
            {searchResults.map((company: Company, index: number) => {
              const { fileNumber, court } = parseFileReference(company.file_reference);
              const isLastItem = index === searchResults.length - 1;

              return (
                // Container for a single company result row
                <Box key={company.id} sx={{ px: 2, py: 2 }}> {/* Padding inside the row */}
                  <Grid container spacing={2}>
                    {/* Left Column */}
                    <Grid item xs={12} md={6}>
                      {/* Person Info (if applicable) */}
                      {lastSearchType === 'person' && company.person && (
                        <>
                          <LabelValue label="Jméno" value={company.person.full_name} isBoldValue/>
                          <LabelValue label="Adresa" value={company.person.address} />
                          <Box sx={{height: '1em'}} /> {/* Spacer */}
                        </>
                      )}
                      {/* Company Info */}
                      <LabelValue label="Název subjektu" value={company.company_name} isBoldValue={!company.person} />
                      <LabelValue label="Spisová značka" value={fileNumber ? `${fileNumber} ${court ? `vedená u ${court}` : ''}`: null} />
                    </Grid>

                    {/* Right Column */}
                    <Grid item xs={12} md={6}>
                      {/* Person Info (if applicable) */}
                      {lastSearchType === 'person' && company.person && (
                        <>
                          <LabelValue label="Datum narození" value={company.person.birth_date} isBoldValue/>
                          <LabelValue label="Angažmá" value={company.person.role} />
                           <Box sx={{height: '1em'}} /> {/* Spacer */}
                        </>
                      )}
                      {/* Company Info */}
                      <LabelValue label="IČO" value={company.ico} isBoldValue />
                      <LabelValue label="Den zápisu" value={company.registration_date} />
                    </Grid>
                  </Grid>

                  {/* Valuation Button - Placed below the grid */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1.5 }}>
                    <Button
                      variant="contained"
                      color="success"
                      size="small" // Make button smaller to fit better
                      onClick={() => handleValuationSelect(company)}
                      disabled={valuationStatus === 'pending'}
                    >
                      Choose this company for valuation
                    </Button>
                  </Box>

                  {/* Divider between items */}
                  {!isLastItem && <Divider sx={{ mt: 2 }} />}
                </Box>
              );
            })}
          </Box> {/* End of border box */}
        </Box>
      )}

      {/* Confirmation Dialog */}
      <Dialog
        open={isDialogOpen}
        onClose={handleCloseDialog}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          Confirm Company Selection
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Are you sure you want to proceed with valuation for {selectedCompany?.company_name} (IČO: {selectedCompany?.ico})?
            This will start the financial document retrieval and analysis process.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} color="inherit">
            Cancel
          </Button>
          <Button onClick={handleConfirmValuation} color="primary" autoFocus>
            Confirm & Start Valuation
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SearchPage;
