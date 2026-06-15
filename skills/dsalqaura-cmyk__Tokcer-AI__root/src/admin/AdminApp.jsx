import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import InternalDashboard from '../pages/InternalDashboard.jsx';
import logo from '../assets/logo.png';
import { supabase } from '../lib/supabase.js';

// Dedicated Admin Login Component
const AdminLogin = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim().toLowerCase(),
        password: password.trim()
      });

      if (authError) {
        setError('Unauthorized access. Invalid admin credentials.');
        setIsLoading(false);
        return;
      }

      // Verifikasi akun yang login adalah admin yang sah
      if (authData.user?.email !== 'admin@tokcer-ai.com') {
        await supabase.auth.signOut();
        setError('Access Denied: You do not have administrative privileges.');
        setIsLoading(false);
        return;
      }

      onLogin();
    } catch (err) {
      console.error('Admin auth error:', err);
      setError('System error during authentication.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4 relative overflow-hidden font-['Inter',sans-serif]">
      {/* Background Decor - consistent with main site */}
      <div className="absolute top-0 left-0 w-full h-full">
        <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-orange-600/10 blur-[120px] rounded-full"></div>
      </div>

      <div className="w-full max-w-md relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <div className="bg-zinc-900/50 backdrop-blur-2xl border border-zinc-800 rounded-[3rem] p-12 shadow-2xl">
          <div className="flex flex-col items-center mb-10">
            <div className="bg-white/5 p-4 rounded-3xl border border-white/10 mb-6">
              <img src={logo} alt="Tokcer AI" className="h-10 w-auto" />
            </div>
            <h2 className="text-2xl font-black text-white tracking-tighter uppercase text-center">Core Command Center</h2>
            <div className="h-1 w-12 bg-blue-600 rounded-full mt-4 shadow-[0_0_12px_rgba(37,99,235,0.8)]"></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">Admin Identity</label>
              <div className="relative group">
                <iconify-icon icon="solar:shield-user-bold-duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 text-xl group-focus-within:text-blue-500 transition-colors"></iconify-icon>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@tokcer-ai.com"
                  className="w-full bg-black/40 border border-zinc-800 rounded-2xl pl-12 pr-6 py-4 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-zinc-700"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">Secret Access Key</label>
              <div className="relative group">
                <iconify-icon icon="solar:lock-keyhole-bold-duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 text-xl group-focus-within:text-blue-500 transition-colors"></iconify-icon>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-black/40 border border-zinc-800 rounded-2xl pl-12 pr-6 py-4 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-zinc-700"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3 text-red-500 animate-in fade-in duration-300">
                <iconify-icon icon="solar:danger-triangle-bold-duotone" className="text-xl"></iconify-icon>
                <p className="text-[10px] font-black uppercase tracking-widest leading-none">{error}</p>
              </div>
            )}

            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full py-5 bg-blue-600 hover:bg-blue-500 text-white font-black uppercase tracking-[0.2em] text-xs rounded-2xl shadow-xl shadow-blue-600/20 transition-all active:scale-95 flex items-center justify-center gap-3 disabled:opacity-50 disabled:active:scale-100"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <iconify-icon icon="solar:shield-check-bold" className="text-xl"></iconify-icon>
                  Authorize Entry
                </>
              )}
            </button>
          </form>
        </div>

        <div className="mt-12 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zinc-900 border border-zinc-800">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Platform Security Protocol Active</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const AdminApp = () => {
  // Use a state that initially forces a check to avoid bypass
  const [isAdminAuth, setIsAdminAuth] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const session = localStorage.getItem('admin_session') === 'true';
    if (session) {
      setIsAdminAuth(true);
    }
    setIsInitializing(false);
  }, []);

  const handleLogin = () => {
    setIsAdminAuth(true);
    localStorage.setItem('admin_session', 'true');
  };

  const handleLogout = () => {
    setIsAdminAuth(false);
    localStorage.removeItem('admin_session');
  };

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center font-['Inter',sans-serif]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(37,99,235,0.3)]"></div>
          <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Securing Connection...</p>
        </div>
      </div>
    );
  }

  // Detect if we are running on the dashboard subdomain or via /admin.html
  const isSubdomain = window.location.hostname === 'dashboard.tokcer-ai.com';
  const basename = window.location.pathname.startsWith('/admin.html') ? '/admin.html' : '/';

  return (
    <Router basename={basename}>
      <Routes>
        <Route 
          path="/" 
          element={
            isAdminAuth ? <Navigate to="/dashboard" replace /> : <AdminLogin onLogin={handleLogin} />
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            isAdminAuth ? <InternalDashboard onLogout={handleLogout} /> : <Navigate to="/" replace />
          } 
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

export default AdminApp;
