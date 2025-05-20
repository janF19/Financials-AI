// src/App.tsx
import React from 'react';
import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
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

// Guards
const ProtectedRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);
  
  if (isLoading) {
    return <div className="flex justify-center items-center h-screen">Loading Authentication...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

const PublicRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);
  
  if (isLoading) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>;
  }
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function App() {
  const dispatch = useAppDispatch();
  
  useEffect(() => {
    dispatch(getProfile());
  }, [dispatch]);
  
  return (
    <Router>
      <ToastContainer position="top-right" autoClose={3000} hideProgressBar={false} newestOnTop={false} closeOnClick rtl={false} pauseOnFocusLoss draggable pauseOnHover />
      <Routes>
        {/* Public routes */}
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
        
        {/* Protected routes */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="process" element={<Process />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="/chat" element={<ChatPage />} /> {/* Add ChatPage route */}
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