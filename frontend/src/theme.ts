import { createTheme } from "@mui/material/styles";

// Create a custom theme with the blue/green color scheme from your existing app
const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2", // Blue color
      light: "#42a5f5",
      dark: "#1565c0",
      contrastText: "#fff",
    },
    secondary: {
      main: "#2e7d32", // Green color
      light: "#4caf50",
      dark: "#1b5e20",
      contrastText: "#fff",
    },
    error: {
      main: "#d32f2f", // Red color
      light: "#ef5350",
      dark: "#c62828",
    },
    warning: {
      main: "#ed6c02", // Orange color
      light: "#ff9800",
      dark: "#e65100",
    },
    background: {
      default: "#f5f5f5",
      paper: "#ffffff",
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: "3rem",
      lineHeight: 1.2,
    },
    h2: {
      fontWeight: 700,
      fontSize: "2.5rem",
      lineHeight: 1.2,
    },
    h3: {
      fontWeight: 600,
      fontSize: "2rem",
      lineHeight: 1.2,
    },
    h4: {
      fontWeight: 600,
      fontSize: "1.5rem",
      lineHeight: 1.2,
    },
    h5: {
      fontWeight: 600,
      fontSize: "1.25rem",
      lineHeight: 1.2,
    },
    h6: {
      fontWeight: 600,
      fontSize: "1rem",
      lineHeight: 1.2,
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: "8px 16px",
        },
        containedPrimary: {
          boxShadow: "0 4px 6px rgba(25, 118, 210, 0.2)",
        },
        containedSecondary: {
          boxShadow: "0 4px 6px rgba(46, 125, 50, 0.2)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.08)",
        },
      },
    },
  },
});

export default theme; 