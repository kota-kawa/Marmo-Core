import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import tokcerLogo from '../assets/logo.png';

const TikTokMockAuth = () => {
  const navigate = useNavigate();
  const [isAuthorizing, setIsAuthorizing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [step, setStep] = useState('login'); // 'login', 'info', 'scanning', 'result'
  const [discoveredShop, setDiscoveredShop] = useState(null);
  const [user, setUser] = useState(null);
  const [loginData, setLoginData] = useState({ identifier: '', password: '' });

  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const isAdmin = localStorage.getItem('tokcer_admin_auth') === 'true';
      if (session) setUser(session.user);
      else if (isAdmin) setUser({ id: 'admin-bypass', email: 'admin@tokcer-ai.com' });
    };
    getUser();
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    setIsAuthorizing(true);
    setTimeout(() => {
      setIsAuthorizing(false);
      setStep('info');
    }, 1500);
  };

  const startScanning = () => {
    setStep('scanning');
    setTimeout(() => {
      setDiscoveredShop({
        name: 'Tokcer Official Store',
        id: 'TTK88' + Math.floor(1000 + Math.random() * 9000),
        region: 'Indonesia (ID)'
      });
      setStep('result');
    }, 2500);
  };

  const handleFinalize = async () => {
    if (!user || !discoveredShop) return;
    setIsAuthorizing(true);
    
    try {
      // Periksa apakah koneksi lama sudah ada agar tidak duplikat
      const { data: existing, error: findError } = await supabase
        .from('marketplace_connections')
        .select('id')
        .eq('user_id', user.id)
        .eq('platform', 'tiktok')
        .maybeSingle();

      if (findError) throw findError;

      let error;
      if (existing?.id) {
        const { error: updateError } = await supabase
          .from('marketplace_connections')
          .update({
            shop_name: discoveredShop.name,
            shop_id: discoveredShop.id,
            sync_status: 'active'
          })
          .eq('id', existing.id);
        error = updateError;
      } else {
        const { error: insertError } = await supabase
          .from('marketplace_connections')
          .insert([{
            user_id: user.id,
            platform: 'tiktok',
            shop_name: discoveredShop.name,
            shop_id: discoveredShop.id,
            sync_status: 'active'
          }]);
        error = insertError;
      }
      
      if (error) throw error;
      
      setIsSuccess(true);
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      alert("Sync Error: " + err.message);
      setIsAuthorizing(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 font-['Inter',sans-serif] relative overflow-hidden">
      {/* Background Aura (Consistent with Landing) */}
      <div className="absolute inset-0 -z-10 bg-black pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-orange-600/10 blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-orange-500/5 blur-[100px]"></div>
      </div>

      <div className="w-full max-w-[480px] bg-zinc-900/50 backdrop-blur-xl border border-zinc-800 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in duration-500">
        
        {/* Header Branding */}
        <div className="p-10 border-b border-zinc-800 bg-black/40">
          <div className="flex items-center justify-center gap-8 mb-10">
            <div className="flex items-center">
              <img src={tokcerLogo} alt="Tokcer AI" className="h-10 w-auto" />
            </div>
            <div className="flex flex-col items-center gap-1 opacity-40">
              <div className="w-8 h-[1px] bg-zinc-500"></div>
              <iconify-icon icon="solar:link-bold" className="text-lg text-zinc-500"></iconify-icon>
              <div className="w-8 h-[1px] bg-zinc-500"></div>
            </div>
            <div className="flex items-center gap-2">
              <div className="bg-black p-2 rounded-xl border border-zinc-800 shadow-lg">
                <iconify-icon icon="ri:tiktok-fill" className="text-3xl text-white"></iconify-icon>
              </div>
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-center text-white mb-3">
            {step === 'login' && "TikTok Shop Login"}
            {step === 'info' && "Authorize Tokcer AI"}
            {step === 'scanning' && "Connecting..."}
            {step === 'result' && !isSuccess && "Connection Found"}
            {isSuccess && "Sync Successful!"}
          </h1>
          <p className="text-xs text-center text-zinc-400 px-6 leading-relaxed">
             {step === 'login' && "Manage your shop and synchronize data with Tokcer AI."}
             {step === 'info' && "TikTok Shop Seller Center Request"}
             {step === 'scanning' && "Fetching shop information from TikTok..."}
             {step === 'result' && !isSuccess && "We found an authorized shop linked to your account."}
             {isSuccess && "Redirecting to your dashboard..."}
          </p>
        </div>

        {/* Content Area */}
        <div className="p-10 min-h-[360px] flex flex-col">
          {step === 'login' && (
             <form onSubmit={handleLogin} className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
                <div>
                   <label className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] block mb-3">Seller Credentials</label>
                   <input 
                      type="text" 
                      required
                      value={loginData.identifier}
                      onChange={(e) => setLoginData({...loginData, identifier: e.target.value})}
                      placeholder="Phone / Email / Username"
                      className="w-full p-4 rounded-2xl bg-black border border-zinc-800 text-sm text-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all placeholder:text-zinc-600"
                   />
                </div>
                <div>
                   <input 
                      type="password" 
                      required
                      value={loginData.password}
                      onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                      placeholder="Password"
                      className="w-full p-4 rounded-2xl bg-black border border-zinc-800 text-sm text-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all placeholder:text-zinc-600"
                   />
                </div>
                <div className="flex items-center justify-between py-1">
                   <button type="button" className="text-xs text-zinc-500 hover:text-white transition-colors">Forgot password?</button>
                   <button type="button" className="text-xs text-orange-500 hover:underline font-bold">Login with code</button>
                </div>
                <button 
                  type="submit"
                  disabled={isAuthorizing}
                  className="w-full py-4 bg-[#FE2C55] hover:bg-[#E11D48] text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-[#FE2C55]/20 transition-all flex items-center justify-center gap-3 active:scale-[0.98]"
                >
                  {isAuthorizing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Verifying...</span>
                    </>
                  ) : (
                    <span>Log in</span>
                  )}
                </button>
             </form>
          )}

          {step === 'info' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="space-y-4 mb-8">
                <div className="flex items-start gap-4 p-4 rounded-2xl bg-black/40 border border-zinc-800">
                  <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center shrink-0">
                    <iconify-icon icon="solar:box-bold" className="text-orange-500 text-xl"></iconify-icon>
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">Product Management</h4>
                    <p className="text-[11px] text-zinc-500 leading-tight">Read and sync your shop products and categories.</p>
                  </div>
                </div>
                <div className="flex items-start gap-4 p-4 rounded-2xl bg-black/40 border border-zinc-800">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0">
                    <iconify-icon icon="solar:cart-large-2-bold" className="text-emerald-500 text-xl"></iconify-icon>
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">Order & Fulfillment</h4>
                    <p className="text-[11px] text-zinc-500 leading-tight">Access orders and manage operational metrics.</p>
                  </div>
                </div>
              </div>
              
              <button 
                onClick={startScanning}
                className="w-full py-4 bg-white text-black hover:bg-zinc-200 rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-xl active:scale-[0.98]"
              >
                Authorize & Connect
              </button>
            </div>
          )}

          {step === 'scanning' && (
            <div className="flex-1 flex flex-col items-center justify-center py-10">
              <div className="relative mb-10">
                <div className="w-24 h-24 rounded-full border-4 border-zinc-800 border-t-orange-500 animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <iconify-icon icon="ri:tiktok-fill" className="text-3xl text-white"></iconify-icon>
                </div>
              </div>
              <p className="text-sm font-medium text-zinc-400 animate-pulse">Scanning shop data...</p>
            </div>
          )}

          {step === 'result' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-8 text-center">
                <iconify-icon icon="solar:check-circle-bold" className="text-4xl text-emerald-500 mb-4"></iconify-icon>
                <h3 className="text-lg font-bold text-white mb-1">{discoveredShop?.name}</h3>
                <p className="text-xs text-zinc-500">ID: {discoveredShop?.id} • {discoveredShop?.region}</p>
              </div>
              
              <button 
                onClick={handleFinalize}
                disabled={isAuthorizing}
                className="w-full py-4 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-orange-600/20 transition-all flex items-center justify-center gap-3 active:scale-[0.98]"
              >
                {isAuthorizing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Finalizing...</span>
                  </>
                ) : (
                  <span>Sync Now</span>
                )}
              </button>
            </div>
          )}
        </div>
        
        {/* Footer info */}
        <div className="p-6 text-center border-t border-zinc-800 bg-black/20">
          <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-medium">
            Secure authorization powered by Tokcer AI & TikTok Shop
          </p>
        </div>
      </div>
    </div>
  );
};

export default TikTokMockAuth;
