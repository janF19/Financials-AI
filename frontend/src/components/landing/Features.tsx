import { Box, Typography, Container, Card, CardContent, CardHeader, Avatar, useTheme } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DescriptionIcon from "@mui/icons-material/Description";
import ChatIcon from "@mui/icons-material/Chat";
import BarChartIcon from "@mui/icons-material/BarChart";
import SecurityIcon from "@mui/icons-material/Security";
import BoltIcon from "@mui/icons-material/Bolt";

const features = [
  {
    icon: <SearchIcon />,
    title: "Company Search & Discovery",
    description: "Search companies by name, person, or ICO number with our comprehensive database",
    color: "primary.main",
    bgColor: "primary.light",
  },
  {
    icon: <DescriptionIcon />,
    title: "Automated Report Generation",
    description: "Generate detailed financial reports and valuations with just a few clicks",
    color: "secondary.main",
    bgColor: "secondary.light",
  },
  {
    icon: <ChatIcon />,
    title: "AI Chat Assistant",
    description: "Get instant answers to financial questions with our intelligent chat interface",
    color: "#9c27b0", // purple
    bgColor: "#f3e5f5",
  },
  {
    icon: <BarChartIcon />,
    title: "Advanced Analytics",
    description: "Deep dive into financial metrics with interactive charts and visualizations",
    color: "warning.main",
    bgColor: "warning.light",
  },
  {
    icon: <SecurityIcon />,
    title: "Enterprise Security",
    description: "Bank-grade security with encrypted data transmission and storage",
    color: "error.main",
    bgColor: "error.light",
  },
  {
    icon: <BoltIcon />,
    title: "Lightning Fast Processing",
    description: "Get results in seconds, not hours, with our optimized AI algorithms",
    color: "#ff9800", // amber
    bgColor: "#fff3e0",
  },
];

export default function Features() {
  const theme = useTheme();

  return (
    <Box id="features" sx={{ py: 8, bgcolor: "background.default" }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: "center", mb: 8 }}>
          <Typography variant="h2" component="h2" sx={{ mb: 2, fontWeight: "bold" }}>
            Powerful Features for Financial Professionals
          </Typography>
          <Typography variant="h5" component="p" color="text.secondary" sx={{ maxWidth: "800px", mx: "auto" }}>
            Everything you need to perform comprehensive financial analysis and company valuations
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: theme.spacing(4) }}>
          {features.map((feature, index) => (
            <Box 
              sx={{ 
                width: { 
                  xs: '100%', 
                  md: `calc((100% - ${theme.spacing(4)}) / 2)`, 
                  lg: `calc((100% - ${theme.spacing(8)}) / 3)` 
                } 
              }} 
              key={index}
            >
              <Card
                sx={{
                  height: "100%",
                  transition: "all 0.3s",
                  "&:hover": {
                    transform: "translateY(-5px)",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.1)",
                  },
                }}
              >
                <CardHeader
                  avatar={
                    <Avatar
                      sx={{
                        bgcolor: feature.bgColor,
                        color: feature.color,
                        opacity: 0.8,
                      }}
                    >
                      {feature.icon}
                    </Avatar>
                  }
                  title={
                    <Typography variant="h6" component="h3">
                      {feature.title}
                    </Typography>
                  }
                />
                <CardContent>
                  <Typography variant="body1" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          ))}
        </Box>
      </Container>
    </Box>
  );
} 