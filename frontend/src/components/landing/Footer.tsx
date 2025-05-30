import { Box, Typography, Container, Button, Link, Divider, useTheme } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export default function Footer() {
  const theme = useTheme();

  return (
    <Box sx={{ bgcolor: "#212121", color: "white", py: 8 }}>
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: theme.spacing(4) }}>
          <Box sx={{ width: { xs: '100%', md: '50%' } }}>
            <Typography
              variant="h4"
              component="h3"
              sx={{
                color: "primary.light",
                fontWeight: "bold",
                mb: 2,
              }}
            >
              Financial Valuation AI
            </Typography>
            <Typography variant="body1" sx={{ color: "grey.400", mb: 4, maxWidth: 500 }}>
              Empowering financial professionals with AI-driven insights and comprehensive valuation tools.
            </Typography>
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button variant="outlined" color="primary" component={RouterLink} to="/login">
                Sign In
              </Button>
              <Button variant="contained" color="primary" component={RouterLink} to="/register">
                Get Started
              </Button>
            </Box>
          </Box>

          <Box sx={{ width: { xs: '100%', sm: '50%', md: '25%' } }}>
            <Typography variant="h6" component="h4" sx={{ mb: 3 }}>
              Product
            </Typography>
            <Box component="ul" sx={{ p: 0, m: 0, listStyle: "none" }}>
              {["Features", "Pricing", "API", "Documentation"].map((item) => (
                <Box component="li" key={item} sx={{ mb: 1.5 }}>
                  <Link
                    href={item === "Features" ? "#features" : item === "Pricing" ? "#pricing" : "#"}
                    underline="hover"
                    sx={{ color: "grey.400", "&:hover": { color: "primary.light" } }}
                  >
                    {item}
                  </Link>
                </Box>
              ))}
            </Box>
          </Box>

          <Box sx={{ width: { xs: '100%', sm: '50%', md: '25%' } }}>
            <Typography variant="h6" component="h4" sx={{ mb: 3 }}>
              Company
            </Typography>
            <Box component="ul" sx={{ p: 0, m: 0, listStyle: "none" }}>
              {["About", "Blog", "Careers", "Contact"].map((item) => (
                <Box component="li" key={item} sx={{ mb: 1.5 }}>
                  <Link 
                    href={item === "About" ? "#about" : "#"} 
                    underline="hover" 
                    sx={{ color: "grey.400", "&:hover": { color: "primary.light" } }}
                  >
                    {item}
                  </Link>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 6, borderColor: "grey.800" }} />

        <Typography variant="body2" align="center" sx={{ color: "grey.500" }}>
          © {new Date().getFullYear()} Financial Valuation AI. All rights reserved.
        </Typography>
      </Container>
    </Box>
  );
} 