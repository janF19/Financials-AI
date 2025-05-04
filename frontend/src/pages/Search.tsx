import React, { useState } from 'react';
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
  InputAdornment,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { searchService } from '../services/api'; // We will add this service next
import { Company, SearchParams } from '../types'; // Import the types

const SearchPage: React.FC = () => {
  const [personName, setPersonName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [ico, setIco] = useState('');
  const [searchResults, setSearchResults] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false); // To know if a search has been performed

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);

  const handleSearch = async (params: SearchParams) => {
    setIsLoading(true);
    setError(null);
    setSearched(true);
    setSearchResults([]); // Clear previous results

    // Basic validation: Ensure at least one field is filled
    if (!params.person_name && !params.company_name && !params.ico) {
        setError('Please enter at least one search criteria.');
        setIsLoading(false);
        return;
    }

    try {
      // Use the actual API call
      const results = await searchService.searchCompanies(params);
      setSearchResults(results);
      if (results.length === 0) {
        setError('No companies found matching your criteria.');
      }
    } catch (err: any) {
      console.error('Search failed:', err);
      setError(err.response?.data?.detail || 'Failed to perform search. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleValuationSelect = (company: Company) => {
    setSelectedCompany(company);
    setIsDialogOpen(true);
  };

  const handleConfirmValuation = () => {
    // TODO: Implement actual navigation or action for valuation
    // For now, just show an alert and close the dialog
    alert(`Proceeding with valuation for ${selectedCompany?.name}`);
    setIsDialogOpen(false);
    setSelectedCompany(null);
    // Example navigation (if you have a valuation route):
    // navigate(`/valuation/${selectedCompany?.id}`);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setSelectedCompany(null);
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
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Enter name"
                variant="outlined"
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
                disabled={isLoading}
              />
              <Button
                variant="contained"
                onClick={() => handleSearch({ person_name: personName })}
                disabled={isLoading || !personName}
                startIcon={<SearchIcon />}
              >
                Search
              </Button>
            </Box>
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
                disabled={isLoading}
              />
              <Button
                variant="contained"
                onClick={() => handleSearch({ company_name: companyName })}
                disabled={isLoading || !companyName}
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
                disabled={isLoading}
              />
              <Button
                variant="contained"
                onClick={() => handleSearch({ ico: ico })}
                disabled={isLoading || !ico}
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
        </Box>
      )}

      {/* Error Message */}
      {error && !isLoading && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}

      {/* Search Results */}
      {searched && !isLoading && !error && searchResults.length > 0 && (
        <Box>
          <Paper elevation={1} sx={{ bgcolor: 'success.main', color: 'white', p: 2, mb: 0, borderBottomLeftRadius: 0, borderBottomRightRadius: 0 }}>
             <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">
                    Search Results: {searchResults.length} compan{searchResults.length === 1 ? 'y' : 'ies'} found
                </Typography>
                {/* You might want to get this date from the API response if available */}
                <Typography variant="caption">Data valid as of {new Date().toLocaleDateString()}</Typography>
             </Box>
          </Paper>
          <Grid container spacing={0}> {/* Use 0 spacing if cards should touch */}
            {searchResults.map((company) => (
              <Grid item xs={12} key={company.id}>
                <Card sx={{ mb: 0, borderRadius: 0, borderTop: 'none' }}> {/* Adjust margin/padding as needed */}
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={7}>
                        <Typography variant="h6" component="div" gutterBottom>
                          {company.name}
                        </Typography>
                        {company.description && (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {company.description}
                          </Typography>
                        )}
                        <Grid container spacing={1} sx={{ fontSize: '0.875rem' }}>
                          {company.file_number && (
                            <>
                              <Grid item xs={4} sm={3}><Typography variant="body2" fontWeight="medium">File number:</Typography></Grid>
                              <Grid item xs={8} sm={9}><Typography variant="body2">{company.file_number} {company.court ? `vedená u ${company.court}` : ''}</Typography></Grid>
                            </>
                          )}
                          {company.address && (
                            <>
                              <Grid item xs={4} sm={3}><Typography variant="body2" fontWeight="medium">Address:</Typography></Grid>
                              <Grid item xs={8} sm={9}><Typography variant="body2">{company.address}</Typography></Grid>
                            </>
                          )}
                        </Grid>
                      </Grid>
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
                               <Grid item xs={5} sm={4}><Typography variant="body2" fontWeight="medium">Registration date:</Typography></Grid>
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
                    >
                      Choose this company for valuation
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
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
            Are you sure you want to proceed with valuation for {selectedCompany?.name}?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleConfirmValuation} color="primary" autoFocus>
            OK
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SearchPage;
