import { useState } from "react";
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  Container,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { Link as RouterLink } from "react-router-dom";

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const navItems = [
    { name: "Features", href: "#features" },
    { name: "Pricing", href: "#pricing" },
    { name: "About", href: "#about" },
  ];

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: "center", p: 2 }}>
      <Typography variant="h6" sx={{ my: 2, color: "primary.main", fontWeight: "bold" }}>
        Financial Valuation AI
      </Typography>
      <List>
        {navItems.map((item) => (
          <ListItem key={item.name} disablePadding>
            <ListItemText
              primary={item.name}
              sx={{
                textAlign: "center",
                "& .MuiTypography-root": {
                  py: 1,
                },
              }}
              primaryTypographyProps={{
                component: "a",
                href: item.href,
                sx: {
                  color: "text.primary",
                  textDecoration: "none",
                  "&:hover": { color: "primary.main" },
                },
              }}
            />
          </ListItem>
        ))}
        <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1 }}>
          <Button variant="outlined" color="primary" component={RouterLink} to="/login">
            Sign In
          </Button>
          <Button variant="contained" color="primary" component={RouterLink} to="/register">
            Get Started
          </Button>
        </Box>
      </List>
    </Box>
  );

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" color="default" elevation={1} sx={{ bgcolor: "background.paper" }}>
        <Container maxWidth="lg">
          <Toolbar disableGutters>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: "primary.main", fontWeight: "bold" }}>
              Financial Valuation AI
            </Typography>

            {/* Desktop Navigation */}
            {!isMobile && (
              <>
                <Box sx={{ display: "flex", mr: 4 }}>
                  {navItems.map((item) => (
                    <Button
                      key={item.name}
                      sx={{
                        color: "text.secondary",
                        mx: 1,
                        "&:hover": { color: "primary.main" },
                      }}
                      href={item.href}
                    >
                      {item.name}
                    </Button>
                  ))}
                </Box>
                <Button color="primary" variant="outlined" sx={{ mr: 2 }} component={RouterLink} to="/login">
                  Sign In
                </Button>
                <Button color="primary" variant="contained" component={RouterLink} to="/register">
                  Get Started
                </Button>
              </>
            )}

            {/* Mobile Navigation */}
            {isMobile && (
              <IconButton color="inherit" aria-label="open drawer" edge="end" onClick={handleDrawerToggle}>
                <MenuIcon />
              </IconButton>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer
        anchor="right"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { boxSizing: "border-box", width: 280 },
        }}
      >
        {drawer}
      </Drawer>
    </Box>
  );
} 