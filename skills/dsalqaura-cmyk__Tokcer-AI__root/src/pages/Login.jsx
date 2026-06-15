import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import logo from '../assets/logo.png';

const Login = () => {
  const [lang, setLang] = useState(localStorage.getItem('tokcer_lang') || 'id');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user'); // 'user' or 'partner'
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [fullName, setFullName] = useState('');
  const [isForgotPass, setIsForgotPass] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const translations = {
    id: {
      loginTitle: "Login Dashboard",
      loginDesc: "Masuk untuk kelola tokomu.",
      emailLabel: "Email Akses",
      passwordLabel: "Password",
      forgotPass: "Lupa Password?",
      loginBtn: "Masuk ke Sistem",
      loggingIn: "Memproses...",
      asUser: "Sebagai User",
      asPartner: "Sebagai Partner",
      noAccount: "Belum punya akun?",
      signUp: "Daftar di sini",
      resetTitle: "Reset Password",
      resetDesc: "Masukkan email untuk menerima instruksi reset password.",
      sendReset: "Kirim Instruksi",
      backToLogin: "Kembali ke Login",
      resetSuccess: "Email instruksi telah dikirim! Silakan cek inbox Anda."
    },
    en: {
      loginTitle: "Dashboard Login",
      loginDesc: "Sign in to manage your shop.",
      emailLabel: "Access Email",
      passwordLabel: "Password",
      forgotPass: "Forgot Password?",
      loginBtn: "Sign In",
      loggingIn: "Processing...",
      asUser: "As User",
      asPartner: "As Partner",
      noAccount: "Don't have an account?",
      signUp: "Sign up here",
      resetTitle: "Reset Password",
      resetDesc: "Enter your email to receive password reset instructions.",
      sendReset: "Send Instructions",
      backToLogin: "Back to Login",
      resetSuccess: "Reset instructions sent! Please check your inbox."
    }
  };

  const t = (key) => translations[lang][key] || key;

  const toggleLang = (newLang) => {
    setLang(newLang);
    localStorage.setItem('tokcer_lang', newLang);
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const isDashboardDomain = window.location.hostname.includes('dashboardstaging');

    const { data: authData, error } = await supabase.auth.signInWithPassword({ email, password });
    
    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      // Logic for admin@tokcer-ai.com
      if (email === 'admin@tokcer-ai.com') {
        localStorage.setItem('tokcer_admin_auth', 'true');
        if (isDashboardDomain) {
          navigate('/admin');
          return;
        }
      }

      // Standard Redirection based on Role Toggle
      if (role === 'partner') {
        // VALIDASI KETAT: Cek apakah benar-benar partner (menggunakan email karena ada inkonsistensi ID)
        const { data: partnerCheck } = await supabase
          .from('partners')
          .select('id')
          .eq('email', authData.user.email)
          .maybeSingle();

        if (!partnerCheck) {
          // Jika bukan partner, batalkan sesi dan berikan eror
          await supabase.auth.signOut();
          setError("Akses Ditolak: Anda tidak terdaftar sebagai Partner.");
          setLoading(false);
          return;
        }
        navigate('/partner-dashboard');
      } else {
        navigate('/dashboard');
      }
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/login?type=recovery',
    });

    if (error) {
      setError(error.message);
    } else {
      setResetSent(true);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4 relative">
      <div className="fixed inset-0 -z-10 h-[100vh] w-full bg-black bg-[linear-gradient(to_right,#27272a_1px,transparent_1px),linear-gradient(to_bottom,#27272a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none"></div>
      
      <div className="absolute top-6 right-6 flex bg-zinc-900 rounded-lg p-1 border border-zinc-800">
        <button onClick={() => toggleLang('id')} className={`px-3 py-1.5 text-[10px] font-bold rounded ${lang === 'id' ? 'bg-orange-600 text-white' : 'text-zinc-500'}`}>ID</button>
        <button onClick={() => toggleLang('en')} className={`px-3 py-1.5 text-[10px] font-bold rounded ${lang === 'en' ? 'bg-orange-600 text-white' : 'text-zinc-500'}`}>EN</button>
      </div>

      <div className="absolute top-6 left-6 lg:fixed">
        <Link to="/" className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          <img src={logo} alt="Tokcer AI" className="h-6 md:h-8 w-auto" />
        </Link>
      </div>

      <div className="relative bg-zinc-900 w-full max-w-[calc(100%-2rem)] md:max-w-sm p-6 md:p-8 rounded-2xl shadow-2xl border border-zinc-800 my-20">
        <div className="mb-6 text-center">
          <div className="w-12 h-12 bg-orange-950/50 rounded-xl flex items-center justify-center border border-orange-900/50 mx-auto mb-4">
            <iconify-icon icon={isForgotPass ? "solar:key-minimalistic-linear" : "solar:user-linear"} className="text-2xl text-orange-500"></iconify-icon>
          </div>
          <h3 className="text-xl md:text-2xl font-semibold text-white tracking-tight">
            {isForgotPass ? t('resetTitle') : t('loginTitle')}
          </h3>
          <p className="text-[10px] md:text-xs text-zinc-400 mt-1">
            {isForgotPass ? t('resetDesc') : t('loginDesc')}
          </p>
        </div>
        
        {!isForgotPass && (
          <div className="flex bg-black rounded-xl p-1 mb-6 border border-zinc-800">
            <button onClick={() => setRole('user')} className={`flex-1 py-2.5 rounded-lg text-xs font-medium transition-all ${role === 'user' ? 'bg-orange-600 text-white' : 'text-zinc-500'}`}>User</button>
            <button onClick={() => setRole('partner')} className={`flex-1 py-2.5 rounded-lg text-xs font-medium transition-all ${role === 'partner' ? 'bg-orange-600 text-white' : 'text-zinc-500'}`}>Partner</button>
          </div>
        )}
        
        {error && <div className="bg-rose-500/10 border border-rose-500/50 text-rose-500 p-3 rounded-lg mb-6 text-sm text-center">{error}</div>}
        {resetSent && <div className="bg-emerald-500/10 border border-emerald-500/50 text-emerald-500 p-3 rounded-lg mb-6 text-sm text-center">{t('resetSuccess')}</div>}

        {!isForgotPass ? (
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('emailLabel')}</label>
              <input type="email" required className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-medium text-zinc-400">{t('passwordLabel')}</label>
                <button type="button" onClick={() => setIsForgotPass(true)} className="text-[10px] text-orange-500 hover:underline">{t('forgotPass')}</button>
              </div>
              <div className="relative">
                <input 
                  type={showPassword ? "text" : "password"} 
                  required 
                  className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none pr-10" 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)} 
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
                >
                  {showPassword ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  )}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="w-full bg-orange-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-orange-500 transition-all flex justify-center items-center gap-2">
              {loading ? t('loggingIn') : t('loginBtn')}
            </button>
          </form>
        ) : (
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('emailLabel')}</label>
              <input type="email" required className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            
            <button type="submit" disabled={loading || resetSent} className="w-full bg-orange-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-orange-500 transition-all flex justify-center items-center gap-2">
              {loading ? t('loggingIn') : t('sendReset')}
            </button>

            <button type="button" onClick={() => { setIsForgotPass(false); setResetSent(false); }} className="w-full text-xs text-zinc-500 hover:text-white transition-colors py-2">
              {t('backToLogin')}
            </button>
          </form>
        )}

        <div className="mt-8 pt-6 border-t border-zinc-800 text-center">
          <p className="text-xs text-zinc-500 mb-3">{t('noAccount')}</p>
          <Link to="/" className="block w-full py-2.5 rounded-xl border border-zinc-800 text-orange-500 font-black text-[10px] uppercase tracking-[0.2em] hover:bg-orange-500/5">
            {t('signUp')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
