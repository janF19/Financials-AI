import {
  Box,
  Typography,
  Container,
  Card,
  CardContent,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  useTheme,
} from "@mui/material";
import PeopleIcon from "@mui/icons-material/People";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import PublicIcon from "@mui/icons-material/Public";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";

const stats = [
  {
    icon: <PeopleIcon fontSize="large"/>,
    value: "10,000+",
    label: "Active Users",
    color: "primary.main",
    bgColor: "primary.light",
  },
  {
    icon: <EmojiEventsIcon fontSize="large"/>,
    value: "99.9%",
    label: "Accuracy Rate",
    color: "secondary.main",
    bgColor: "secondary.light",
  },
  {
    icon: <PublicIcon fontSize="large"/>,
    value: "50+",
    label: "Countries",
    color: "#9c27b0", // purple
    bgColor: "#f3e5f5",
  },
  {
    icon: <LightbulbIcon fontSize="large"/>,
    value: "1M+",
    label: "Reports Generated",
    color: "warning.main",
    bgColor: "warning.light",
  },
];

export default function About() {
  const theme = useTheme();

  return (
    <Box id="about" sx={{ py: 8, bgcolor: "background.default" }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: "center", mb: 8 }}>
          <Typography variant="h2" component="h2" sx={{ mb: 2, fontWeight: "bold" }}>
            About Financial Valuation AI
          </Typography>
          <Typography variant="h5" component="p" color="text.secondary" sx={{ maxWidth: "800px", mx: "auto", mb: 6 }}>
            We're revolutionizing financial analysis with cutting-edge AI technology, making professional-grade
            valuations accessible to everyone.
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: theme.spacing(4), mb: 8 }}>
          {stats.map((stat, index) => (
            <Box 
              sx={{ 
                width: { 
                  xs: `calc((100% - ${theme.spacing(4)}) / 2)`, 
                  md: `calc((100% - ${theme.spacing(8)}) / 3)` 
                } 
              }} 
              key={index}
            >
              <Card sx={{ height: "100%", textAlign: "center" }}>
                <CardContent>
                  <Avatar
                    sx={{
                      bgcolor: stat.bgColor,
                      color: stat.color,
                      width: 56,
                      height: 56,
                      mx: "auto",
                      mb: 2,
                      opacity: 0.7
                    }}
                  >
                    {stat.icon}
                  </Avatar>
                  <Typography variant="h4" component="p" sx={{ fontWeight: "bold", mb: 1 }}>
                    {stat.value}
                  </Typography>
                  <Typography variant="body1" color="text.secondary">
                    {stat.label}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          ))}
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: theme.spacing(6), alignItems: "center" }}>
          <Box sx={{ width: { xs: '100%', md: `calc((100% - ${theme.spacing(6)}) / 2)` } }}>
            <Typography variant="h4" component="h3" sx={{ mb: 3, fontWeight: "bold" }}>
              Our Mission
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              We believe that powerful financial analysis tools shouldn't be limited to large institutions. Our
              AI-powered platform democratizes access to sophisticated valuation models and insights, enabling
              professionals of all sizes to make informed investment decisions.
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Built by a team of financial experts and AI researchers, our platform combines decades of industry
              experience with the latest advances in machine learning and natural language processing.
            </Typography>

            <List>
              <ListItem disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <FiberManualRecordIcon sx={{ color: "primary.main", fontSize: 12 }} />
                </ListItemIcon>
                <ListItemText primary="Advanced AI algorithms trained on millions of financial data points" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <FiberManualRecordIcon sx={{ color: "secondary.main", fontSize: 12 }} />
                </ListItemIcon>
                <ListItemText primary="Real-time market data integration for accurate valuations" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <FiberManualRecordIcon sx={{ color: "#9c27b0", fontSize: 12 }} />
                </ListItemIcon>
                <ListItemText primary="Intuitive interface designed for financial professionals" />
              </ListItem>
            </List>
          </Box>

          <Box sx={{ width: { xs: '100%', md: `calc((100% - ${theme.spacing(6)}) / 2)` } }}>
            <Paper
              elevation={0}
              sx={{
                p: 4,
                borderRadius: 4,
                background: "linear-gradient(to bottom right, #e3f2fd, #f3e5f5)", // Example gradient
              }}
            >
              <Typography variant="h5" component="h4" sx={{ mb: 3, fontWeight: "bold" }}>
                Why Choose Us?
              </Typography>
              <List>
                <ListItem>
                  <Avatar sx={{ bgcolor: "primary.main", mr: 2, color: "white" }}>1</Avatar>
                  <ListItemText primary="Industry-leading accuracy with 99.9% precision rate" />
                </ListItem>
                <ListItem>
                  <Avatar sx={{ bgcolor: "secondary.main", mr: 2, color: "white" }}>2</Avatar>
                  <ListItemText primary="Lightning-fast processing with results in seconds" />
                </ListItem>
                <ListItem>
                  <Avatar sx={{ bgcolor: "#9c27b0", mr: 2, color: "white" }}>3</Avatar>
                  <ListItemText primary="Comprehensive support and training resources" />
                </ListItem>
              </List>
            </Paper>
          </Box>
        </Box>
      </Container>
    </Box>
  );
} 