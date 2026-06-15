import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { supabase } from './lib/supabase.js';
import Landing from './pages/Landing.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import PartnerDashboard from './pages/PartnerDashboard.jsx';
import InternalDashboard from './pages/InternalDashboard.jsx';
import AdminLogin from './pages/AdminLogin.jsx';
import PartnerAgreement from './pages/PartnerAgreement.jsx';
import TikTokMockAuth from './pages/TikTokMockAuth.jsx';
import TikTokCallback from './pages/TikTokCallback.jsx';
import HppCalculator from './pages/HppCalculator.jsx';
import { TermsPage, PrivacyPage, RefundPage } from './pages/LegalPages.jsx';
import FaqPage from './pages/FaqPage.jsx';

const ProtectedRoute = ({ children }) => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const checkSession = async () => {
      const timeout = setTimeout(() => {
        if (mounted) setLoading(false);
      }, 3000);

      try {
        const { data: { session: currentSession } } = await supabase.auth.getSession();
        if (mounted) {
          setSession(currentSession);
          setLoading(false);
        }
      } catch (err) {
        console.error("Session check error:", err);
        if (mounted) setLoading(false);
      } finally {
        clearTimeout(timeout);
      }
    };
    checkSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(prev => {
        if (prev?.access_token !== currentSession?.access_token) {
          return currentSession;
        }
        return prev;
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const isAdminAuth = localStorage.getItem('tokcer_admin_auth') === 'true';
  const isPathAdmin = window.location.pathname.startsWith('/admin');

  // If user is trying to access /admin, they MUST have admin auth flag set
  // This blocks regular logged-in users from accessing admin routes
  if (isPathAdmin && !isAdminAuth) {
    return <Navigate to="/admin-login" replace />;
  }

  // Regular users/partners redirect to standard login if no session
  if (!isPathAdmin && !loading && !session && !isAdminAuth) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  const host = window.location.hostname;
  const isInternalAdminDomain = host === 'dashboardstaging.tokcer-ai.com' || host === 'dashboard.tokcer-ai.com' || host === 'www.dashboard.tokcer-ai.com';

  if (isInternalAdminDomain) {
    return (
      <Router>
        <Routes>
          <Route path="/" element={<Navigate to="/admin-login" replace />} />
          <Route path="/admin-login" element={<AdminLogin />} />
          <Route path="/admin" element={<ProtectedRoute><InternalDashboard /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/admin-login" replace />} />
        </Routes>
      </Router>
    );
  }

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/register" element={<Landing />} />
        <Route path="/partner-agreement" element={<PartnerAgreement />} />
        <Route path="/login" element={<Login />} />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/partner-dashboard" 
          element={
            <ProtectedRoute>
              <PartnerDashboard />
            </ProtectedRoute>
          } 
        />
        
        {/* Legal Pages */}
        <Route path="/tiktok-auth-mock" element={<TikTokMockAuth />} />
        <Route path="/tiktok-callback" element={<TikTokCallback />} />
        <Route path="/hpp-calculator" 
          element={
            <ProtectedRoute>
              <HppCalculator />
            </ProtectedRoute>
          } 
        />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/refund" element={<RefundPage />} />
        <Route path="/faq" element={<FaqPage />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
