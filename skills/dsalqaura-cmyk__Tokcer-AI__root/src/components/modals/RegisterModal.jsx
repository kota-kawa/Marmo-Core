import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const RegisterModal = ({ isOpen, onClose, selectedPlan }) => {
  const { t } = useLandingTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); 
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [storeLinks, setStoreLinks] = useState({});
  const [formPlan, setFormPlan] = useState(selectedPlan || 'starter');
  const [dbPlans, setDbPlans] = useState([]);
  const [affiliateId, setAffiliateId] = useState(localStorage.getItem('tokcer_affiliate_id') || '');
  const [billingCycle, setBillingCycle] = useState('Monthly');
  const [isBusinessVerified, setIsBusinessVerified] = useState(false);

  const [isSnapLoaded, setIsSnapLoaded] = useState(false);

  // 1. Dynamic Script Loading & Environment Detection
  const isSandbox = window.location.hostname.includes('staging');
  const MIDTRANS_CLIENT_KEY = isSandbox 
    ? 'Mid-client-w0fhy-qm6_MgWzGY' 
    : 'Mid-client-kIWFreS7VE0iNHP0';
  const SNAP_SCRIPT_URL = isSandbox 
    ? 'https://app.sandbox.midtrans.com/snap/snap.js' 
    : 'https://app.midtrans.com/snap/snap.js';

  useEffect(() => {
    if (!isOpen) return;

    // Load Snap script dynamically
    const script = document.createElement('script');
    script.src = SNAP_SCRIPT_URL;
    script.setAttribute('data-client-key', MIDTRANS_CLIENT_KEY);
    script.async = true;
    script.onload = () => setIsSnapLoaded(true);
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, [isOpen]);

  // Fetch Pricing Plans from DB
  useEffect(() => {
    const fetchPlans = async () => {
      const { data } = await supabase.from('pricing_plans').select('*');
      if (data) setDbPlans(data);
    };
    fetchPlans();
  }, []);

  useEffect(() => {
    if (selectedPlan) {
      const planId = typeof selectedPlan === 'string' ? selectedPlan : (selectedPlan?.id || 'starter');
      setFormPlan(planId);
    }
  }, [selectedPlan]);

  if (!isOpen) return null;

  const handlePlatformToggle = (platform) => {
    if (selectedPlatforms.includes(platform)) {
      setSelectedPlatforms(selectedPlatforms.filter(p => p !== platform));
      const newLinks = { ...storeLinks };
      delete newLinks[platform];
      setStoreLinks(newLinks);
    } else {
      setSelectedPlatforms([...selectedPlatforms, platform]);
    }
  };

  const handleLinkChange = (platform, value) => {
    setStoreLinks({ ...storeLinks, [platform]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isSnapLoaded) {
      setStatus("Tunggu sebentar, sistem pembayaran sedang dimuat...");
      return;
    }
    setLoading(true);
    setStatus(null);

    const formData = new FormData(e.target);
    const email = formData.get('email');
    const nama = formData.get('nama');
    const phone = formData.get('phone');
    const planValue = formPlan || 'starter';
    const billing_cycle = formData.get('billing_cycle') || 'Monthly';
    
    const business_type = formData.get('business_type');
    
    // 1. Basic Validations
    if (selectedPlatforms.length === 0) {
        setLoading(false);
        setStatus("Pilih minimal satu platform jualan.");
        return;
    }

    try {
      // 2. IF STARTER (FREE) -> Just insert to clients table as usual
      if (planValue === 'starter') {
        const { data, error } = await supabase.functions.invoke('register-starter', {
          body: { 
            nama, 
            email, 
            phone, 
            platforms: selectedPlatforms, 
            storeLinks, 
            affiliateId 
          }
        });
        if (error || !data?.success) {
          throw new Error(error?.message || data?.error || "Gagal mengaktifkan akun Starter Anda secara otomatis.");
        }
        setStatus('success');
        return;
      }

      // 3. IF PAID PLAN (PRO/ELITE/ULTIMATE) -> Call Midtrans Edge Function
      const currentPlanData = dbPlans.find(p => p.id === planValue);
      
      // HARDCODED FALLBACK PRICES (Safety Guard)
      const fallbackPrices = {
        pro: { Monthly: 499000, Yearly: 5489000 },
        elite: { Monthly: 999000, Yearly: 10989000 },
        ultimate: { Monthly: 1999000, Yearly: 21989000 }
      };

      const amount = billing_cycle === 'Monthly' 
        ? (currentPlanData?.price_monthly || fallbackPrices[planValue]?.Monthly || 499000) 
        : (currentPlanData?.price_yearly || fallbackPrices[planValue]?.Yearly || 5489000);
      
      const tokens = (planValue === 'pro' ? 300 : planValue === 'elite' ? 1000 : 3000);

      // Call Supabase Edge Function to get Snap Token
      const { data: snapData, error: snapError } = await supabase.functions.invoke('midtrans-init', {
        body: { 
            plan_name: planValue, 
            amount: amount, 
            tokens: tokens,
            is_sandbox: isSandbox, // Kirim flag sandbox ke server
            user_data: { nama, email, phone, platforms: selectedPlatforms, storeLinks, affiliateId, business_type, billing_cycle }
        }
      });

      if (snapError) throw new Error("Gagal menghubungi server pembayaran. Coba lagi nanti.");

      // 4. Open Midtrans Snap Modal
      if (window.snap) {
        window.snap.pay(snapData.token, {
          onSuccess: (result) => {
            console.log('success', result);
            setStatus('success');
          },
          onPending: (result) => {
            console.log('pending', result);
            setStatus('pending_payment');
          },
          onError: (result) => {
            console.error('error', result);
            setStatus('Payment failed. Please try again.');
          },
          onClose: () => {
            setLoading(false);
          }
        });
      } else {
        throw new Error("Midtrans script not loaded.");
      }

    } catch (error) {
      console.error(error);
      setStatus(error.message || "Terjadi kesalahan sistem.");
      setLoading(false);
    }
  };

  const platformOptions = [
    { id: 'TikTok', label: 'TikTok Shop', icon: 'ri:tiktok-fill' },
    { id: 'Shopee', label: 'Shopee', icon: 'simple-icons:shopee' },
    { id: 'Instagram', label: 'Instagram', icon: 'ri:instagram-fill' },
    { id: 'Other', label: 'Lainnya', icon: 'solar:menu-dots-bold' }
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative bg-zinc-900 w-full max-w-xl p-4 sm:p-6 md:p-8 rounded-2xl shadow-2xl border border-zinc-800 max-h-[92vh] overflow-y-auto custom-scrollbar">
        <button onClick={onClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors">
          <iconify-icon icon="solar:close-circle-linear" className="text-2xl"></iconify-icon>
        </button>
        
        <div className="mb-6 text-center">
          <div className="w-12 h-12 bg-orange-950/50 rounded-xl flex items-center justify-center border border-orange-900/50 mx-auto mb-4">
            <iconify-icon icon="solar:card-send-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
          </div>
          <h3 className="text-xl md:text-2xl font-semibold text-white tracking-tight">Daftar & Berlangganan</h3>
          <p className="text-[10px] md:text-xs text-zinc-400 mt-1">Selesaikan pembayaran untuk akses instan ke dashboard.</p>
        </div>
        
        {status === 'success' || status === 'pending_payment' ? (
          <div className="bg-orange-500/10 border border-orange-500/50 rounded-xl p-6 text-center animate-in zoom-in duration-300">
            <div className="w-12 h-12 bg-orange-500/20 text-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <iconify-icon icon={status === 'success' ? "solar:check-circle-bold" : "solar:clock-circle-bold"} className="text-2xl"></iconify-icon>
            </div>
            <h4 className="text-lg font-semibold text-white mb-2">
                {status === 'success' ? "Pendaftaran Berhasil!" : "Menunggu Pembayaran"}
            </h4>
            <p className="text-sm text-zinc-400">
                {status === 'success' 
                    ? "Pembayaran Anda telah terverifikasi. Silakan cek email untuk instruksi login."
                    : "Silakan selesaikan pembayaran Anda di aplikasi pembayaran. Akun Anda akan aktif otomatis setelah sukses."}
            </p>
            <button onClick={onClose} className="mt-6 w-full py-3 rounded-xl bg-orange-600 text-white text-sm font-bold hover:bg-orange-500 transition-all">Tutup</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {status && typeof status === 'string' && (
              <div className="bg-rose-500/10 border border-rose-500/50 text-rose-500 p-3 rounded-lg text-sm text-center">{status}</div>
            )}
            
            {/* Form Fields (Identity) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Nama Lengkap</label>
                <input type="text" name="nama" required className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" placeholder="Andi Pratama" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">No. WA</label>
                <input type="tel" name="phone" required className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" placeholder="0812..." />
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Email Aktif</label>
              <input type="email" name="email" required className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" placeholder="email@example.com" />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Kode Partner (Opsional)</label>
              <input type="text" value={affiliateId} onChange={(e) => setAffiliateId(e.target.value)} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:ring-2 focus:ring-orange-500/50 outline-none" placeholder="Contoh: TKC-AGR-128258" />
            </div>

            {/* Plan Selection */}
            <div className={`grid grid-cols-1 ${formPlan !== 'starter' ? 'md:grid-cols-2' : ''} gap-4`}>
                <div>
                    <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Paket</label>
                    <select value={formPlan} onChange={(e) => { setFormPlan(e.target.value); if (e.target.value === 'starter') setBillingCycle('Monthly'); }} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm appearance-none outline-none">
                        <option value="starter">Starter (Gratis)</option>
                        <option value="pro">Pro Edition ({billingCycle === 'Monthly' ? 'Rp 499k' : 'Rp 5.489k'})</option>
                        <option value="elite">Elite Edition ({billingCycle === 'Monthly' ? 'Rp 999k' : 'Rp 10.989k'})</option>
                        <option value="ultimate">Ultimate Edition ({billingCycle === 'Monthly' ? 'Rp 1.999k' : 'Rp 21.989k'})</option>
                    </select>
                </div>
                {formPlan !== 'starter' && (
                <div>
                    <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Siklus</label>
                    <select name="billing_cycle" value={billingCycle} onChange={(e) => setBillingCycle(e.target.value)} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm appearance-none outline-none">
                        <option value="Monthly">Bulanan</option>
                        <option value="Yearly">Tahunan</option>
                    </select>
                </div>
                )}
            </div>

            {/* Platform Selection */}
            <div className="space-y-4">
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Platform Jualan</label>
              <div className="grid grid-cols-2 gap-3">
                {platformOptions.map((plat) => (
                  <label key={plat.id} className={`flex items-center gap-3 p-3 border rounded-xl cursor-pointer transition-all ${selectedPlatforms.includes(plat.id) ? 'bg-orange-600/10 border-orange-500/50 text-white' : 'bg-black border-zinc-800 text-zinc-500'}`}>
                    <input type="checkbox" checked={selectedPlatforms.includes(plat.id)} onChange={() => handlePlatformToggle(plat.id)} className="hidden" />
                    <iconify-icon icon={plat.icon} className="text-lg"></iconify-icon>
                    <span className="text-xs font-medium">{plat.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Business Verification Checkbox */}
            <div className="bg-zinc-900/50 p-4 rounded-xl border border-zinc-800 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="flex-shrink-0 mt-0.5">
                  <input 
                    type="checkbox" 
                    checked={isBusinessVerified}
                    onChange={(e) => setIsBusinessVerified(e.target.checked)}
                    className="w-4 h-4 rounded bg-black border-zinc-700 text-orange-600 focus:ring-orange-600 focus:ring-offset-zinc-900" 
                  />
                </div>
                <div className="text-xs text-zinc-400 group-hover:text-zinc-300 transition-colors leading-relaxed">
                  Saya menyatakan bahwa toko saya sudah berstatus <span className="text-white font-bold">Akun Bisnis / Lolos Verifikasi</span> di marketplace yang ingin saya integrasikan.
                </div>
              </label>
              
              {!isBusinessVerified && (
                <div className="flex items-start gap-2 text-[10px] text-amber-500/90 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20">
                  <iconify-icon icon="solar:danger-triangle-bold" className="text-sm flex-shrink-0 mt-0.5"></iconify-icon>
                  <p><strong>Peringatan:</strong> Jika akun marketplace Anda belum terverifikasi sebagai akun bisnis, sistem Tokcer AI beresiko tidak dapat menarik data produk dan penjualan secara otomatis.</p>
                </div>
              )}
            </div>

            <button type="submit" disabled={loading || !isBusinessVerified} className="w-full bg-orange-600 text-white py-4 rounded-2xl text-sm font-black uppercase tracking-[0.2em] hover:bg-orange-500 transition-all flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading && <iconify-icon icon="solar:spinner-linear" className="animate-spin text-lg"></iconify-icon>}
              {loading ? "MENYIAPKAN PEMBAYARAN..." : "DAFTAR & BAYAR SEKARANG"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default RegisterModal;
