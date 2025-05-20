import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import BusinessIcon from '@mui/icons-material/Business'; // For DPH/Dotace
import DescriptionIcon from '@mui/icons-material/Description'; // For Justice Info
import LanguageIcon from '@mui/icons-material/Language'; // For Web Analysis
import InfoIcon from '@mui/icons-material/Info';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'; // For Justice Ministry
import GavelIcon from '@mui/icons-material/Gavel'; // For Legal Form etc.
import EventIcon from '@mui/icons-material/Event';
import AssignmentIcon from '@mui/icons-material/Assignment'; // For Spisova Znacka
import ListAltIcon from '@mui/icons-material/ListAlt'; // For Predmet Podnikani
import PeopleIcon from '@mui/icons-material/People'; // For Statutarni Organ
import { SvgIconComponent } from '@mui/icons-material'; // Import SvgIconComponent
import MonetizationOnIcon from '@mui/icons-material/MonetizationOn'; // For Zakladni Kapital
import PaymentIcon from '@mui/icons-material/Payment'; // For Splaceno
import PersonPinIcon from '@mui/icons-material/PersonPin'; // For Jediny Akcionar
import ArticleIcon from '@mui/icons-material/Article'; // For Akcie

import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { fetchCompanyInfo, clearCompanyInfo, setIcoQuery as setStoreIcoQuery } from '../store/slices/companyInfoSlice';
import { 
  CompanyAllInfoResponse, 
  JusticeInfo, 
  DphInfo, 
  DotaceInfo, 
  WebSearchAnalysis, 
  JusticeInfoStatutarniOrgan, 
  JusticeInfoStatutarniOrganClen,
  JusticeInfoJedinyAkcionar,
  JusticeInfoAkcieItem
} from '../types/index.ts';
import { toast } from 'react-toastify';

// Helper component for consistent label-value display
const DetailItem: React.FC<{ label: string; value?: string | null | number; icon?: React.ReactNode, fullWidth?: boolean }> = ({ label, value, icon, fullWidth }) => {
  if (value === null || typeof value === 'undefined' || value === '') return null;
  return (
    <Box 
      sx={{ 
        width: { 
          xs: '100%', 
          sm: fullWidth ? '100%' : '50%', 
          md: fullWidth ? '100%' : '33.33%' 
        }, 
        p: 1 /* Replicates spacing from Grid item */ 
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        {icon && <ListItemIcon sx={{minWidth: '36px'}}>{icon}</ListItemIcon>}
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'medium' }}>
          {label}:
        </Typography>
      </Box>
      <Typography variant="body1" sx={{ pl: icon ? '36px' : 0, wordBreak: 'break-word' }}>{String(value)}</Typography>
    </Box>
  );
};

interface SectionCardProps {
  title: string;
  icon?: React.ReactElement<React.SVGProps<SVGSVGElement> & { sx?: object }>; // More specific type for MUI icons
  children: React.ReactNode;
}

const SectionCard: React.FC<SectionCardProps> = ({ title, icon, children }) => (
  <Paper elevation={2} sx={{ mb: 3 }}>
    <Box sx={{ backgroundColor: 'primary.main', color: 'primary.contrastText', p: 2, display: 'flex', alignItems: 'center', borderTopLeftRadius: (theme) => theme.shape.borderRadius, borderTopRightRadius: (theme) => theme.shape.borderRadius }}>
      {icon && React.cloneElement(icon, { sx: { ...icon.props.sx, mr: 1 } })}
      <Typography variant="h6">{title}</Typography>
    </Box>
    <Box sx={{ p: 2 }}>{children}</Box>
  </Paper>
);


const CompanyInfoPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const { data: companyData, isLoading, error, icoQuery: storeIcoQuery } = useAppSelector((state) => state.companyInfo);
  const [localIco, setLocalIco] = useState('');
  const [currentTab, setCurrentTab] = useState(0);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);

  useEffect(() => {
    // Clear data when component unmounts or ICO changes significantly
    return () => {
      // dispatch(clearCompanyInfo()); // Decide if you want to clear on unmount
    };
  }, [dispatch]);

  const handleSearchClick = () => {
    if (!localIco.trim()) {
      toast.warn('Please enter an IČO.');
      return;
    }
    if (!/^\d{8}$/.test(localIco.trim())) {
      toast.warn('IČO must be an 8-digit number.');
      return;
    }
    dispatch(setStoreIcoQuery(localIco.trim()));
    setIsConfirmDialogOpen(true);
  };

  const handleConfirmSearch = () => {
    setIsConfirmDialogOpen(false);
    if (storeIcoQuery) {
      dispatch(fetchCompanyInfo(storeIcoQuery));
    }
  };

  const handleCloseConfirmDialog = () => {
    setIsConfirmDialogOpen(false);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const renderStatutarniOrgan = (statOrgan: JusticeInfoStatutarniOrgan | string | null | undefined) => {
    if (!statOrgan) return <Typography>Not available</Typography>;
    if (typeof statOrgan === 'string') return <Typography sx={{wordBreak: 'break-word'}}>{statOrgan}</Typography>;

    const organ = statOrgan as JusticeInfoStatutarniOrgan; // Type assertion

    return (
      <Box>
        {organ.pocet_clenu && <Typography variant="body2" gutterBottom><strong>Počet členů:</strong> {organ.pocet_clenu}</Typography>}
        {organ.zpusob_jednani && <Typography variant="body2" gutterBottom><strong>Způsob jednání:</strong> {organ.zpusob_jednani}</Typography>}
        {organ.clenove && organ.clenove.length > 0 && (
          <Box mt={1}>
            <Typography variant="subtitle2" gutterBottom>Členové:</Typography>
            <List dense disablePadding>
              {organ.clenove.map((clen, index) => (
                <ListItem key={index} disableGutters sx={{ display: 'block', borderLeft: '2px solid', borderColor: 'primary.light', pl: 1, mb: 1 }}>
                  {clen.jmeno_prijmeni && <ListItemText primary={`${clen.role ? clen.role + ': ' : ''}${clen.jmeno_prijmeni}`} />}
                  {clen.datum_narozeni && <ListItemText secondary={`Datum narození: ${clen.datum_narozeni}`} />}
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Box>
    );
  };


  const renderJusticeInfo = (justiceInfo?: JusticeInfo | null) => {
    if (!justiceInfo) return <Alert severity="info">No justice ministry information available.</Alert>;
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', mx: -1 /* Negative margin to counteract item padding */ }}>
        <DetailItem label="Obchodní firma" value={justiceInfo.obchodni_firma} icon={<BusinessIcon />} />
        <DetailItem label="IČO" value={justiceInfo.identifikacni_cislo} icon={<InfoIcon />} />
        <DetailItem label="Právní forma" value={justiceInfo.pravni_forma} icon={<GavelIcon />} />
        <DetailItem label="Datum vzniku a zápisu" value={justiceInfo.datum_vzniku_a_zapisu} icon={<EventIcon />} />
        <DetailItem label="Spisová značka" value={justiceInfo.spisova_znacka} icon={<AssignmentIcon />} />
        <DetailItem label="Sídlo" value={justiceInfo.sídlo?.adresa_kompletni} icon={<BusinessIcon />} fullWidth />
        
        {/* Basic Capital and Paid Up */}
        <DetailItem label="Základní kapitál" value={justiceInfo.zakladni_kapital} icon={<MonetizationOnIcon />} />
        <DetailItem label="Splaceno" value={justiceInfo.splaceno} icon={<PaymentIcon />} />
        
        {justiceInfo.predmet_podnikani && justiceInfo.predmet_podnikani.length > 0 && (
          <Box sx={{ width: '100%', px: 1, mt: 1 }}>
            <Accordion sx={{mt: 2}}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <ListAltIcon sx={{mr:1}} /> <Typography fontWeight="medium">Předmět podnikání</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <List dense>
                  {justiceInfo.predmet_podnikani.map((item, index) => (
                    <ListItem key={index}><ListItemText primary={item} /></ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {justiceInfo.statutarni_organ_predstavenstvo && (
          <Box sx={{ width: '100%', px: 1, mt: 1 }}>
            <Accordion sx={{mt: 2}}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <PeopleIcon sx={{mr:1}} /> <Typography fontWeight="medium">Statutární orgán</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {renderStatutarniOrgan(justiceInfo.statutarni_organ_predstavenstvo)}
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {/* Sole Shareholder (Jediný akcionář) */}
        {justiceInfo.jediny_akcionar && (
          <Box sx={{ width: '100%', px: 1, mt: 1 }}>
            <Accordion sx={{mt: 2}}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <PersonPinIcon sx={{mr:1}} /> <Typography fontWeight="medium">Jediný akcionář</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {typeof justiceInfo.jediny_akcionar === 'string' ? (
                  <Typography sx={{wordBreak: 'break-word'}}>{justiceInfo.jediny_akcionar}</Typography>
                ) : justiceInfo.jediny_akcionar ? (
                  <Box>
                    <Typography variant="body2" gutterBottom sx={{wordBreak: 'break-word'}}><strong>Název:</strong> {(justiceInfo.jediny_akcionar as JusticeInfoJedinyAkcionar).nazev || 'N/A'}</Typography>
                    <Typography variant="body2" gutterBottom sx={{wordBreak: 'break-word'}}><strong>IČ:</strong> {(justiceInfo.jediny_akcionar as JusticeInfoJedinyAkcionar).ic || 'N/A'}</Typography>
                    <Typography variant="body2" sx={{wordBreak: 'break-word'}}><strong>Adresa:</strong> {(justiceInfo.jediny_akcionar as JusticeInfoJedinyAkcionar).adresa || 'N/A'}</Typography>
                  </Box>
                ) : (
                  <Typography>Not available</Typography>
                )}
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

        {/* Shares (Akcie) */}
        {justiceInfo.akcie && justiceInfo.akcie.length > 0 && (
          <Box sx={{ width: '100%', px: 1, mt: 1 }}>
            <Accordion sx={{mt: 2}}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <ArticleIcon sx={{mr:1}} /> <Typography fontWeight="medium">Akcie</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <List dense>
                  {justiceInfo.akcie.map((akcie_item, index) => {
                    if (typeof akcie_item === 'string') {
                      return (
                        <ListItem key={index}>
                          <ListItemText primary={akcie_item} sx={{wordBreak: 'break-word'}} />
                        </ListItem>
                      );
                    } else if (akcie_item) {
                      const item = akcie_item as JusticeInfoAkcieItem;
                      return (
                        <ListItem key={index} sx={{ display: 'block', mb: 1, borderLeft: '2px solid', borderColor: 'divider', pl: 1}}>
                          {item.popis_akcie && (
                            <Typography variant="body2" sx={{ whiteSpace: 'pre-line', wordBreak: 'break-word' }}>
                              <strong>Popis:</strong> {item.popis_akcie}
                            </Typography>
                          )}
                          {item.podminky_prevodu && (
                            <Typography variant="body2" color="text.secondary" sx={{wordBreak: 'break-word'}}>
                              <strong>Podmínky převodu:</strong> {item.podminky_prevodu}
                            </Typography>
                          )}
                           {!item.popis_akcie && !item.podminky_prevodu && (
                             <Typography variant="body2" color="text.secondary">Detail akcie není k dispozici.</Typography>
                           )}
                        </ListItem>
                      );
                    }
                    return null;
                  })}
                </List>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}

         {/* Add more accordions for dozorci_rada, prokura, ostatni_skutecnosti as needed */}
      </Box>
    );
  };

  const renderDphAndDotaceInfo = (dphInfo?: DphInfo | null, dotaceInfo?: DotaceInfo | null) => {
    if (!dphInfo && !dotaceInfo) return <Alert severity="info">No DPH or subsidy information available.</Alert>;
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', mx: -1 }}>
        {dphInfo && (
          <>
            <DetailItem label="Registrace k DPH od" value={dphInfo.registrace_od_data} />
            <DetailItem label="Nespolehlivý plátce DPH" value={dphInfo.nespolehlivy_platce ?? "N/A"} />
          </>
        )}
        {dotaceInfo && (
          <DetailItem label="Dotace uvolněná" value={dotaceInfo.uvolnena !== null && typeof dotaceInfo.uvolnena !== 'undefined' ? `${dotaceInfo.uvolnena.toLocaleString()} Kč` : "Žádné informace"} />
        )}
      </Box>
    );
  };

  const renderWebAnalysis = (webAnalysis?: WebSearchAnalysis | null) => {
    if (!webAnalysis || !webAnalysis.summary || webAnalysis.summary.length === 0) {
      return <Alert severity="info">No web analysis summary available.</Alert>;
    }
    return (
      <Box>
        {webAnalysis.name && <Typography variant="h6" gutterBottom>{webAnalysis.name}</Typography>}
        <List>
          {webAnalysis.summary.map((item, index) => (
            <React.Fragment key={index}>
              <ListItem alignItems="flex-start">
                <ListItemText primary={item} />
              </ListItem>
              {index < webAnalysis.summary!.length - 1 && <Divider component="li" />}
            </React.Fragment>
          ))}
        </List>
      </Box>
    );
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Company Information Research
      </Typography>
      
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Search Company by IČO
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Enter the company's 8-digit IČO to retrieve detailed information.
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, mt: 2, alignItems: 'center', flexDirection: { xs: 'column', sm: 'row' } }}>
          <TextField
            fullWidth
            label="Enter IČO"
            variant="outlined"
            value={localIco}
            onChange={(e) => setLocalIco(e.target.value)}
            disabled={isLoading}
            size="small"
            sx={{ flex: {sm: 1} }}
            inputProps={{ maxLength: 8 }}
            onKeyPress={(event) => {
              if (event.key === 'Enter') {
                handleSearchClick();
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleSearchClick}
            disabled={isLoading || !localIco.trim()}
            startIcon={<SearchIcon />}
            sx={{ width: { xs: '100%', sm: 'auto' } }}
          >
            Search
          </Button>
        </Box>
      </Paper>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4, alignItems: 'center' }}>
          <CircularProgress />
          <Typography sx={{ ml: 2 }}>Collecting company data from registers and web sources...</Typography>
        </Box>
      )}

      {error && !isLoading && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}

      {!isLoading && !error && companyData && (
        <Box sx={{ mt: 4 }}>
          <Paper elevation={1} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={currentTab} onChange={handleTabChange} aria-label="company information tabs" variant="fullWidth">
              <Tab icon={<DescriptionIcon />} iconPosition="start" label="Business Registry" disabled={!companyData.justice_info} />
              <Tab icon={<BusinessIcon />} iconPosition="start" label="VAT & Subsidies" disabled={!companyData.dph_info && !companyData.dotace_info} />
              <Tab icon={<LanguageIcon />} iconPosition="start" label="Web Analysis" disabled={!companyData.web_search_analysis} />
            </Tabs>
          </Paper>

          <Box sx={{ py: 3 }}>
            {currentTab === 0 && (
              <SectionCard title="Business Registry Information" icon={<AccountBalanceIcon />}>
                {renderJusticeInfo(companyData.justice_info)}
              </SectionCard>
            )}
            {currentTab === 1 && (
              <SectionCard title="VAT and Subsidy Information" icon={<BusinessIcon />}>
                {renderDphAndDotaceInfo(companyData.dph_info, companyData.dotace_info)}
              </SectionCard>
            )}
            {currentTab === 2 && (
              <SectionCard title="Web Search Analysis" icon={<LanguageIcon />}>
                {renderWebAnalysis(companyData.web_search_analysis)}
              </SectionCard>
            )}
          </Box>
        </Box>
      )}
       {!isLoading && !error && companyData && Object.values(companyData).every(value => value === null || (typeof value === 'object' && value !== null && Object.keys(value).length === 0) || (Array.isArray(value) && value.length === 0) ) && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          No information found for the provided IČO: {storeIcoQuery}. The company may not exist or data is currently unavailable.
        </Alert>
      )}


      <Dialog open={isConfirmDialogOpen} onClose={handleCloseConfirmDialog}>
        <DialogTitle>Confirm Data Collection</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Do you want to start collecting data for IČO: <strong>{storeIcoQuery}</strong>? This process might take a few moments.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseConfirmDialog} color="inherit">Cancel</Button>
          <Button onClick={handleConfirmSearch} color="primary" autoFocus>
            Confirm & Start
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CompanyInfoPage; 