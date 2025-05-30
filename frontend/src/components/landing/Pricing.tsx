import {
  Box,
  Typography,
  Container,
  Card,
  CardContent,
  CardHeader,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  useTheme,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import { Link as RouterLink } from "react-router-dom";

const plans = [
  {
    name: "Starter",
    price: "$29",
    period: "/month",
    description: "Perfect for individual analysts and small teams",
    features: [
      "Up to 50 company searches per month",
      "Basic valuation reports",
      "Email support",
      "Standard AI chat assistant",
      "Export to PDF",
    ],
    popular: false,
    buttonLink: "/register?plan=starter", // Example link
  },
  {
    name: "Professional",
    price: "$99",
    period: "/month",
    description: "Ideal for growing financial firms and consultants",
    features: [
      "Up to 500 company searches per month",
      "Advanced valuation models",
      "Priority support",
      "Advanced AI chat with custom prompts",
      "Export to multiple formats",
      "API access",
    ],
    popular: true,
    buttonLink: "/register?plan=professional", // Example link
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large organizations with specific needs",
    features: [
      "Unlimited company searches",
      "Custom valuation models",
      "Dedicated account manager",
      "White-label solutions",
      "Advanced security features",
      "Custom integrations",
      "SLA guarantee",
    ],
    popular: false,
    buttonLink: "/contact-sales", // Example link
  },
];

export default function Pricing() {
  const theme = useTheme();

  return (
    <Box id="pricing" sx={{ py: 8, bgcolor: "background.paper" }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: "center", mb: 8 }}>
          <Typography variant="h2" component="h2" sx={{ mb: 2, fontWeight: "bold" }}>
            Simple, Transparent Pricing
          </Typography>
          <Typography variant="h5" component="p" color="text.secondary" sx={{ maxWidth: "800px", mx: "auto" }}>
            Choose the plan that fits your needs. All plans include our core AI-powered features.
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: theme.spacing(4), justifyContent: "center" }}>
          {plans.map((plan, index) => (
            <Box
              sx={{
                width: { 
                  xs: '100%', 
                  md: `calc((100% - ${theme.spacing(8)}) / 3)` 
                },
                ...(plan.popular
                  ? {
                      transform: { md: "scale(1.05)" },
                      zIndex: 1,
                    }
                  : {}),
              }}
              key={index}
            >
              <Card
                sx={{
                  height: "100%",
                  position: "relative",
                  overflow: "visible",
                  border: plan.popular ? "2px solid" : "1px solid",
                  borderColor: plan.popular ? "primary.main" : "divider",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                {plan.popular && (
                  <Box
                    sx={{
                      position: "absolute",
                      top: 0,
                      left: "50%",
                      transform: "translate(-50%, -50%)",
                      zIndex: 2,
                    }}
                  >
                    <Chip
                      label="Most Popular"
                      color="primary"
                      sx={{
                        fontWeight: "bold",
                        px: 2,
                        height: 32,
                        borderRadius: 16,
                        boxShadow: 1,
                      }}
                    />
                  </Box>
                )}

                <CardHeader
                  title={
                    <Typography variant="h5" component="h3" align="center">
                      {plan.name}
                    </Typography>
                  }
                  subheader={
                    <Box sx={{ textAlign: "center", mt: 2 }}>
                      <Typography variant="h3" component="p" sx={{ fontWeight: "bold" }}>
                        {plan.price}
                        <Typography variant="body1" component="span" color="text.secondary">
                          {plan.period}
                        </Typography>
                      </Typography>
                      <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                        {plan.description}
                      </Typography>
                    </Box>
                  }
                  sx={{
                    pb: 0,
                    pt: plan.popular ? theme.spacing(3.5) : theme.spacing(2),
                  }}
                />

                <CardContent sx={{ pt: 2, flexGrow: 1, display: "flex", flexDirection: "column" }}>
                  <List sx={{ mb: 2, flexGrow: 1 }}>
                    {plan.features.map((feature, featureIndex) => (
                      <ListItem key={featureIndex} disableGutters>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <CheckIcon color="success" />
                        </ListItemIcon>
                        <ListItemText primary={feature} />
                      </ListItem>
                    ))}
                  </List>

                  <Button
                    variant={plan.popular ? "contained" : "outlined"}
                    color={plan.popular ? "primary" : "inherit"}
                    fullWidth
                    size="large"
                    component={RouterLink}
                    to={plan.buttonLink}
                  >
                    {plan.name === "Enterprise" ? "Contact Sales" : "Get Started"}
                  </Button>
                </CardContent>
              </Card>
            </Box>
          ))}
        </Box>
      </Container>
    </Box>
  );
} 