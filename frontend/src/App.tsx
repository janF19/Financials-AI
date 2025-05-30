// src/App.tsx
import React from 'react';
import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import { useAppDispatch, useAppSelector } from './hooks/redux.ts';
import { getProfile } from './store/slices/authSlice';

import ChatPage from './pages/ChatPage';

// @ts-ignore
import Dashboard from './pages/Dashboard';
// @ts-ignore
import Login from './pages/Login';
// @ts-ignore
import Register from './pages/Register';
// @ts-ignore
import Reports from './pages/Reports';
// @ts-ignore
import Process from './pages/Process';
// @ts-ignore
import SearchPage from './pages/Search';
// @ts-ignore
import Profile from './pages/Profile';
// @ts-ignore
import NotFound from './pages/NotFound';
// @ts-ignore
import Layout from './components/Layout.tsx';

import CompanyInfoPage from './pages/CompanyInfoPage.tsx';
import LandingPage from './pages/LandingPage';

// Guards - Simplified as isLoading is handled globally in App
const ProtectedRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  // isLoading check removed, handled in App component

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

const PublicRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated } = useAppSelector((state) => state.auth);
  // isLoading check removed, handled in App component

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function App() {
  const dispatch = useAppDispatch();
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);

  useEffect(() => {
    dispatch(getProfile());
  }, [dispatch]);

  if (isLoading) {
    return <div className="flex justify-center items-center h-screen">Loading Authentication...</div>;
  }

  return (
    <Router>
      {/* CssBaseline can be global if desired, or scoped with ThemeProvider */}
      {/* <CssBaseline /> */}
      <ToastContainer position="top-right" autoClose={3000} hideProgressBar={false} newestOnTop={false} closeOnClick rtl={false} pauseOnFocusLoss draggable pauseOnHover />
      <Routes>
        {/* Route 1: Handles the root path ("/") */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <ThemeProvider theme={theme}>
                <CssBaseline />
                <LandingPage />
              </ThemeProvider>
            )
          }
        />

        {/* Public routes (Login, Register) - Not wrapped by the new theme by default */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          }
        />

        {/* Protected application routes that use the Layout component */}
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="process" element={<Process />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="info" element={<CompanyInfoPage />} />
          <Route path="profile" element={<Profile />} />
        </Route>

        {/* 404 page */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;