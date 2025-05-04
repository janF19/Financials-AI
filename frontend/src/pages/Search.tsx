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
  Snackbar
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
          <Grid item xs={12}>
            <Typography variant="body1" gutterBottom>
              Search company based on participation by person name:
            </Typography>
            <Grid container spacing={2} alignItems="center">
                 <Grid item xs={12} sm={5}>
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
                 <Grid item xs={12} sm={5}>
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
                 <Grid item xs={12} sm={2}>
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
          <Grid item xs={12}>
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
      {/* Show results only if not loading, no error, and a search has been performed (lastSearchType is set) */}
      {!isLoading && !error && lastSearchType && searchResults.length > 0 && (
        <Box>
          <Paper elevation={1} sx={{ bgcolor: 'success.dark', color: 'white', p: 2, mb: 0, borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>
             <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">
                    Search Results: {searchResults.length} compan{searchResults.length === 1 ? 'y' : 'ies'} found
                </Typography>
                <Typography variant="caption">Data retrieved {new Date().toLocaleTimeString()}</Typography>
             </Box>
          </Paper>
          <Grid container spacing={0}>
            {searchResults.map((company: Company) => {
              const { fileNumber, court } = parseFileReference(company.file_reference);
              return (
                <Grid item xs={12} key={company.id}> {/* Use company.id (which is ICO) as key */}
                  <Card sx={{ mb: 0, borderRadius: 0, borderTop: 'none', border: '1px solid', borderColor: 'divider' }}>
                    <CardContent>
                      <Grid container spacing={2}>
                        {/* Left Column: Main Info */}
                        <Grid item xs={12} md={7}>
                          <Typography variant="h6" component="div" gutterBottom>
                            {company.company_name}
                          </Typography>
                          {/* Display Person Info if available (from person search) */}
                          {lastSearchType === 'person' && company.person && (
                             <Box sx={{ mb: 2, p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}>
                                <Typography variant="body2" fontWeight="medium" gutterBottom>Associated Person:</Typography>
                                <Typography variant="body2"><strong>Name:</strong> {company.person.full_name}</Typography>
                                {company.person.role && <Typography variant="body2"><strong>Role:</strong> {company.person.role}</Typography>}
                                {company.person.birth_date && <Typography variant="body2"><strong>Born:</strong> {company.person.birth_date}</Typography>}
                                {company.person.address && <Typography variant="body2"><strong>Address:</strong> {company.person.address}</Typography>}
                             </Box>
                          )}
                          {/* File Number and Address */}
                          <Grid container spacing={1} sx={{ fontSize: '0.875rem' }}>
                            {fileNumber && (
                              <>
                                <Grid item xs={4} sm={3}><Typography variant="body2" fontWeight="medium">File number:</Typography></Grid>
                                <Grid item xs={8} sm={9}><Typography variant="body2">{fileNumber} {court ? `vedená u ${court}` : ''}</Typography></Grid>
                              </>
                            )}
                            {/* Assuming address might be on company object directly or derived */}
                            {/* {company.address && (
                              <>
                                <Grid item xs={4} sm={3}><Typography variant="body2" fontWeight="medium">Address:</Typography></Grid>
                                <Grid item xs={8} sm={9}><Typography variant="body2">{company.address}</Typography></Grid>
                              </>
                            )} */}
                          </Grid>
                        </Grid>
                        {/* Right Column: ICO and Dates */}
                        <Grid item xs={12} md={5}>
                           <Grid container spacing={1} sx={{ fontSize: '0.875rem' }}>
                             {company.ico && (
                               <>
                                 <Grid item xs={5} sm={4}><Typography variant="body2" fontWeight="medium">IČO:</Typography></Grid>
                                 <Grid item xs={7} sm={8}><Typography variant="body2" fontWeight="bold">{company.ico}</Typography></Grid>
                               </>
                             )}
                             {company.registration_date && (
                               <>
                                 <Grid item xs={5} sm={4}><Typography variant="body2" fontWeight="medium">Registration:</Typography></Grid>
                                 <Grid item xs={7} sm={8}><Typography variant="body2">{company.registration_date}</Typography></Grid>
                               </>
                             )}
                           </Grid>
                        </Grid>
                      </Grid>
                    </CardContent>
                    <CardActions sx={{ justifyContent: 'flex-end', bgcolor: 'action.hover', p: 2 }}>
                      <Button
                        variant="contained"
                        color="success"
                        onClick={() => handleValuationSelect(company)}
                        disabled={valuationStatus === 'pending'} // Disable while valuation is pending
                      >
                        Choose this company for valuation
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
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
