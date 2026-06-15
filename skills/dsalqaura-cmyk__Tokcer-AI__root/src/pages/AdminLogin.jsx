import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import logo from '../assets/logo.png';

const AdminLogin = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAdminAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const cleanEmail = email.trim().toLowerCase();

    try {
      // 1. Autentikasi via Supabase (password divalidasi di server, tidak pernah ada di kode)
      const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email: cleanEmail,
        password: password.trim()
      });

      if (authError) {
        setError('Access Denied: ' + authError.message);
        setLoading(false);
        return;
      }

      // 2. Verifikasi bahwa user yang login adalah admin yang sah
      if (authData.user?.email !== 'admin@tokcer-ai.com') {
        // Bukan admin — paksa logout dan tolak akses
        await supabase.auth.signOut();
        setError('Access Denied: You do not have administrative privileges.');
        setLoading(false);
        return;
      }

      // 3. Admin terverifikasi — set flag dan arahkan ke dashboard
      localStorage.setItem('tokcer_admin_auth', 'true');
      navigate('/admin');

    } catch (err) {
      console.error("Auth error:", err);
      setError("System error during authentication.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#050505] px-4 relative overflow-hidden font-sans">
      {/* Abstract Background Effects */}
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_50%_0%,#1e3a8a33_0%,transparent_50%)] pointer-events-none"></div>
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none"></div>

      <div className="relative w-full max-w-md animate-in fade-in zoom-in-95 duration-700">
        <div className="text-center mb-10">
          <Link to="/">
            <img src={logo} alt="Tokcer AI" className="h-10 mx-auto mb-6 drop-shadow-[0_0_15px_rgba(37,99,235,0.3)]" />
          </Link>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-600/10 border border-blue-500/20 rounded-full mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
            <span className="text-[10px] font-black text-blue-400 uppercase tracking-[0.2em]">Administrative Access</span>
          </div>
          <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Core Command <span className="text-blue-500">Center</span></h2>
          <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-2">Secure Gateway • Version 2.4.1</p>
        </div>

        <div className="bg-zinc-900/40 backdrop-blur-2xl border border-zinc-800 p-10 rounded-[2.5rem] shadow-2xl relative">
          {/* Accent Line */}
          <div className="absolute top-0 left-10 right-10 h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>

          <form onSubmit={handleAdminAuth} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1">Admin ID / Email</label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-blue-500 transition-colors">
                  <iconify-icon icon="solar:shield-user-bold-duotone" className="text-xl"></iconify-icon>
                </div>
                <input 
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-black/60 border border-zinc-800 focus:border-blue-500/50 rounded-2xl pl-12 pr-6 py-4 text-sm text-white placeholder-zinc-700 transition-all outline-none"
                  placeholder="admin@tokcer-ai.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1">Security Key / Password</label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-blue-500 transition-colors">
                  <iconify-icon icon="solar:key-bold-duotone" className="text-xl"></iconify-icon>
                </div>
                <input 
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-black/60 border border-zinc-800 focus:border-blue-500/50 rounded-2xl pl-12 pr-6 py-4 text-sm text-white placeholder-zinc-700 transition-all outline-none"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                <iconify-icon icon="solar:danger-bold" className="text-red-500 text-lg"></iconify-icon>
                <p className="text-[10px] font-black text-red-500 uppercase tracking-widest">{error}</p>
              </div>
            )}

            <button 
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-black uppercase tracking-[0.3em] py-5 rounded-2xl shadow-xl shadow-blue-600/20 transition-all flex items-center justify-center gap-3 group active:scale-95"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span> Authenticating...</>
              ) : (
                <><iconify-icon icon="solar:lock-password-bold-duotone" className="text-xl group-hover:rotate-12 transition-transform"></iconify-icon> Initiate Access</>
              )}
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <Link to="/login" className="text-[10px] font-black text-zinc-600 hover:text-zinc-400 uppercase tracking-widest transition-colors flex items-center justify-center gap-2">
            <iconify-icon icon="solar:arrow-left-linear"></iconify-icon>
            Back to Public Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
