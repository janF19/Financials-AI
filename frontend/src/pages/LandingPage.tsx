import Header from "../components/landing/Header";
import Hero from "../components/landing/Hero";
import Features from "../components/landing/Features";
import Pricing from "../components/landing/Pricing";
import About from "../components/landing/About";
import Footer from "../components/landing/Footer";
import { Box } from "@mui/material";

export default function LandingPage() {
  return (
    <Box>
      <Header />
      <main>
        <Hero />
        <Features />
        <Pricing />
        <About />
      </main>
      <Footer />
    </Box>
  );
} 