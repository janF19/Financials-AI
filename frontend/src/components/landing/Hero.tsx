import { Box, Typography, Button, Container, Paper, useTheme, useMediaQuery } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import PsychologyIcon from "@mui/icons-material/Psychology";
import BarChartIcon from "@mui/icons-material/BarChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { Link as RouterLink } from "react-router-dom";

export default function Hero() {
  const theme = useTheme();
  // const isMobile = useMediaQuery(theme.breakpoints.down("md")); // Not used in this version

  return (
    <Box
      sx={{
        py: { xs: 8, md: 12 },
        background: "linear-gradient(to bottom right, #e3f2fd, #ffffff)",
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ textAlign: "center", mb: 8 }}>
          <Typography
            variant="h1"
            component="h1"
            sx={{
              mb: 2,
              fontSize: { xs: "2.5rem", md: "3.5rem" },
              fontWeight: "bold",
            }}
          >
            AI-Powered Financial
            <Typography
              variant="h1"
              component="span"
              color="primary"
              sx={{
                display: "block",
                fontSize: "inherit",
                fontWeight: "inherit",
              }}
            >
              Valuation Platform
            </Typography>
          </Typography>

          <Typography
            variant="h5"
            component="p"
            color="text.secondary"
            sx={{
              mb: 4,
              maxWidth: "800px",
              mx: "auto",
              fontSize: { xs: "1.1rem", md: "1.25rem" },
            }}
          >
            Transform your financial analysis with cutting-edge AI technology. Get accurate company valuations,
            comprehensive reports, and intelligent insights in minutes.
          </Typography>

          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              gap: 2,
              justifyContent: "center",
              mb: 8,
            }}
          >
            <Button
              variant="contained"
              color="primary"
              size="large"
              endIcon={<ArrowForwardIcon />}
              sx={{ px: 4, py: 1.5 }}
              component={RouterLink}
              to="/register" // Or your desired "get started" / "free trial" link
            >
              Start Free Trial
            </Button>
            <Button variant="outlined" color="primary" size="large" sx={{ px: 4, py: 1.5 }} href="#features"> {/* Or a link to a demo page/video */}
              Watch Demo
            </Button>
          </Box>

          {/* Feature Icons */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: theme.spacing(4), mt: 4 }}>
            <Box sx={{ width: { xs: '100%', md: `calc((100% - ${theme.spacing(8)}) / 3)` } }}>
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Paper
                  elevation={0}
                  sx={{
                    bgcolor: "primary.light",
                    p: 2,
                    borderRadius: "50%",
                    mb: 2,
                    opacity: 0.2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <PsychologyIcon sx={{ fontSize: 40, color: "primary.main" }} />
                </Paper>
                <Typography variant="h6" component="h3" sx={{ mb: 1 }}>
                  AI-Driven Analysis
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ textAlign: "center" }}>
                  Advanced machine learning algorithms for precise financial modeling
                </Typography>
              </Box>
            </Box>

            <Box sx={{ width: { xs: '100%', md: `calc((100% - ${theme.spacing(8)}) / 3)` } }}>
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Paper
                  elevation={0}
                  sx={{
                    bgcolor: "secondary.light",
                    p: 2,
                    borderRadius: "50%",
                    mb: 2,
                    opacity: 0.2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <BarChartIcon sx={{ fontSize: 40, color: "secondary.main" }} />
                </Paper>
                <Typography variant="h6" component="h3" sx={{ mb: 1 }}>
                  Comprehensive Reports
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ textAlign: "center" }}>
                  Detailed valuation reports with actionable insights and recommendations
                </Typography>
              </Box>
            </Box>

            <Box sx={{ width: { xs: '100%', md: `calc((100% - ${theme.spacing(8)}) / 3)` } }}>
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Paper
                  elevation={0}
                  sx={{
                    bgcolor: "warning.light",
                    p: 2,
                    borderRadius: "50%",
                    mb: 2,
                    opacity: 0.2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <TrendingUpIcon sx={{ fontSize: 40, color: "warning.main" }} />
                </Paper>
                <Typography variant="h6" component="h3" sx={{ mb: 1 }}>
                  Real-time Data
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ textAlign: "center" }}>
                  Live market data integration for up-to-date financial analysis
                </Typography>
              </Box>
            </Box>
          </Box>
        </Box>
      </Container>
    </Box>
  );
} 