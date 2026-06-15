import React, { useState, useEffect } from 'react';

const BillingTab = ({ profile, clientData, supabase, t }) => {
  const [loading, setLoading] = useState(false);
  const [midtransClientKey, setMidtransClientKey] = useState('');

  // Default plan: hindari 'demo' atau 'starter' karena tidak ada di daftar plans
  const currentActivePlan = (clientData?.plan || profile?.subscription_plan || 'starter').toLowerCase();
  const validUpgradePlans = ['pro', 'elite', 'ultimate'];
  const defaultSelectedPlan = validUpgradePlans.includes(currentActivePlan) ? currentActivePlan : 'pro';

  const [selectedPlan, setSelectedPlan] = useState(defaultSelectedPlan);
  const [billingCycle, setBillingCycle] = useState(clientData?.billing_cycle || 'Monthly');
  const [isSnapLoaded, setIsSnapLoaded] = useState(false);

  const isSandbox = window.location.hostname.includes('staging') || window.location.hostname.includes('localhost');
  // Fallback ke hardcoded jika ai_configs belum diisi
  const MIDTRANS_CLIENT_KEY = midtransClientKey || (isSandbox
    ? 'Mid-client-w0fhy-qm6_MgWzGY'
    : 'Mid-client-kIWFreS7VE0iNHP0');
  const SNAP_SCRIPT_URL = isSandbox
    ? 'https://app.sandbox.midtrans.com/snap/snap.js'
    : 'https://app.midtrans.com/snap/snap.js';

  // Ambil Midtrans client key dari ai_configs
  useEffect(() => {
    const fetchMidtransKey = async () => {
      try {
        const keyName = isSandbox ? 'midtrans_client_key_sandbox' : 'midtrans_client_key';
        const { data } = await supabase
          .from('ai_configs')
          .select('value')
          .eq('key', keyName)
          .maybeSingle();
        if (data?.value) setMidtransClientKey(data.value);
      } catch (err) {
        // Fallback ke hardcoded key jika gagal
        console.warn('Gagal ambil Midtrans client key dari DB, pakai fallback.');
      }
    };
    fetchMidtransKey();
  }, [isSandbox]);

  useEffect(() => {
    const existingScript = document.querySelector(`script[src="${SNAP_SCRIPT_URL}"]`);
    if (existingScript) {
      setIsSnapLoaded(true);
      return;
    }

    const script = document.createElement('script');
    script.src = SNAP_SCRIPT_URL;
    script.setAttribute('data-client-key', MIDTRANS_CLIENT_KEY);
    script.async = true;
    script.onload = () => setIsSnapLoaded(true);
    document.head.appendChild(script);

    return () => {
      if (document.head.contains(script)) {
        document.head.removeChild(script);
      }
    };
  }, []);

  const plans = [
    { id: 'pro', name: 'Pro Edition', monthly: 499000, yearly: 5489000 },
    { id: 'elite', name: 'Elite Edition', monthly: 999000, yearly: 10989000 },
    { id: 'ultimate', name: 'Ultimate Edition', monthly: 1999000, yearly: 21989000 }
  ];

  const handlePay = async () => {
    if (!isSnapLoaded) {
      alert("Sistem pembayaran sedang dimuat. Harap tunggu sebentar.");
      return;
    }

    setLoading(true);
    try {
      const planData = plans.find(p => p.id === selectedPlan);
      const amount = billingCycle === 'Monthly' ? planData.monthly : planData.yearly;
      const tokens = selectedPlan === 'pro' ? 300 : selectedPlan === 'elite' ? 1000 : 3000;

      const { data: snapData, error: snapError } = await supabase.functions.invoke('midtrans-init', {
        body: { 
            plan_name: selectedPlan, 
            amount: amount, 
            tokens: tokens,
            is_sandbox: isSandbox,
            user_data: { 
                user_id: profile.id,
                client_id: clientData?.id,
                nama: profile.full_name || clientData?.shop_name, 
                email: profile.email, 
                phone: clientData?.whatsapp || '08000000000', 
                billing_cycle: billingCycle,
                is_renewal: true
            }
        }
      });

      if (snapError) throw new Error("Gagal menghubungi server pembayaran.");

      if (window.snap) {
        window.snap.pay(snapData.token, {
          onSuccess: (result) => {
            alert('Pembayaran sukses! Halaman akan dimuat ulang.');
            window.location.reload();
          },
          onPending: () => alert('Menunggu pembayaran...'),
          onError: () => alert('Pembayaran gagal.'),
          onClose: () => alert('Anda menutup pop-up pembayaran.')
        });
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const isPartnerBenefit = profile?.role === 'partner' && clientData?.payment_method === 'partner_benefit';
  const benefitExpiry = clientData?.expires_at || clientData?.expired_at;
  const isBenefitActive = isPartnerBenefit && benefitExpiry && new Date(benefitExpiry) > new Date();

  const validExpiryDate = clientData?.expires_at || clientData?.expired_at;
  const isExpired = clientData?.status === 'expired' || (validExpiryDate && new Date(validExpiryDate) < new Date());
  const isNearExpiry = !isExpired && validExpiryDate && new Date(validExpiryDate).getTime() - new Date().getTime() < 3 * 24 * 60 * 60 * 1000;

  // Partner dalam masa benefit — tampilkan info benefit, jangan tampilkan form bayar
  if (isBenefitActive) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 bg-orange-500/10 rounded-xl border border-orange-500/20">
            <iconify-icon icon="solar:medal-ribbons-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Partner Benefit Aktif</h2>
            <p className="text-zinc-400 text-sm">Anda sedang menikmati Ultimate Plan sebagai benefit Partner</p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-orange-600/10 to-amber-600/5 border border-orange-500/30 rounded-2xl p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-orange-500/20 rounded-2xl flex items-center justify-center mx-auto">
            <iconify-icon icon="solar:crown-bold-duotone" className="text-4xl text-orange-500"></iconify-icon>
          </div>
          <h3 className="text-2xl font-black text-white">Ultimate Plan</h3>
          <p className="text-zinc-400 text-sm max-w-md mx-auto">
            Sebagai Partner Tokcer AI, Anda mendapatkan akses Ultimate Plan secara gratis selama 2 bulan sebagai benefit registrasi.
          </p>
          <div className="bg-black/40 border border-orange-500/20 rounded-xl p-4 inline-block">
            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1">Benefit Berakhir</p>
            <p className="text-xl font-black text-orange-400">
              {new Date(benefitExpiry).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
          </div>
          <p className="text-[11px] text-zinc-600 italic">
            Tidak ada tagihan selama masa benefit berlangsung. Setelah berakhir, tim Tokcer AI akan menghubungi Anda untuk informasi kelanjutan.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2.5 bg-orange-500/10 rounded-xl border border-orange-500/20">
          <iconify-icon icon="solar:card-2-bold-duotone" className="text-2xl text-orange-500"></iconify-icon>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Billing & Langganan</h2>
          <p className="text-zinc-400 text-sm">Kelola paket langganan dan siklus tagihan Anda</p>
        </div>
      </div>

      {isExpired && (
        <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-xl flex items-start gap-4">
            <iconify-icon icon="solar:danger-triangle-bold" className="text-2xl text-red-500 shrink-0"></iconify-icon>
            <div>
                <h3 className="text-red-400 font-bold">Masa Aktif Berakhir</h3>
                <p className="text-red-400/80 text-sm mt-1">Masa aktif langganan Anda sudah habis. Silakan lakukan perpanjangan di bawah agar sistem AI dan integrasi toko dapat digunakan kembali tanpa kendala.</p>
            </div>
        </div>
      )}

      {isNearExpiry && (
        <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl flex items-start gap-4">
            <iconify-icon icon="solar:bell-bing-bold" className="text-2xl text-amber-500 shrink-0"></iconify-icon>
            <div>
                <h3 className="text-amber-400 font-bold">Mendekati Jatuh Tempo</h3>
                <p className="text-amber-400/80 text-sm mt-1">Langganan Anda akan berakhir dalam waktu kurang dari 3 hari. Segera perpanjang agar tidak mengganggu operasional bisnis Anda.</p>
            </div>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 relative overflow-hidden">
        {/* Glow Effect */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/5 blur-[100px] rounded-full pointer-events-none"></div>
        
        <h3 className="text-lg font-bold text-white mb-4 relative z-10">Informasi Langganan Saat Ini</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
            <div className="bg-zinc-950/80 p-5 rounded-xl border border-zinc-800/80 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-2">
                    <iconify-icon icon="solar:box-minimalistic-linear" className="text-zinc-500"></iconify-icon>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Paket Aktif</p>
                </div>
                <p className="text-2xl text-white font-bold capitalize">{clientData?.plan || profile?.subscription_plan || 'Starter'}</p>
            </div>
            <div className="bg-zinc-950/80 p-5 rounded-xl border border-zinc-800/80 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-2">
                    <iconify-icon icon="solar:calendar-date-linear" className="text-zinc-500"></iconify-icon>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Siklus Tagihan</p>
                </div>
                <p className="text-2xl text-white font-bold">{clientData?.billing_cycle === 'Yearly' ? 'Tahunan' : 'Bulanan'}</p>
            </div>
            <div className="bg-zinc-950/80 p-5 rounded-xl border border-zinc-800/80 backdrop-blur-sm">
                <div className="flex items-center gap-2 mb-2">
                    <iconify-icon icon="solar:clock-circle-linear" className="text-zinc-500"></iconify-icon>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Jatuh Tempo</p>
                </div>
                <p className={`text-xl font-bold ${isExpired ? 'text-red-500' : isNearExpiry ? 'text-amber-500' : 'text-emerald-500'}`}>
                    {validExpiryDate ? new Date(validExpiryDate).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '-'}
                </p>
            </div>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-2">Perpanjang / Ganti Paket</h3>
        <p className="text-zinc-400 text-sm mb-6">Pilih paket yang Anda inginkan untuk memperpanjang masa aktif. Anda juga bisa menaikkan (Upgrade) atau menurunkan (Downgrade) langganan Anda di sini.</p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="space-y-1.5">
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Pilih Paket</label>
                <div className="relative">
                    <select 
                        value={selectedPlan} 
                        onChange={e => setSelectedPlan(e.target.value)} 
                        className="w-full pl-4 pr-10 py-3.5 rounded-xl border border-zinc-700 bg-zinc-950 text-white text-sm outline-none focus:border-orange-500 appearance-none transition-colors"
                    >
                        {plans.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                    <iconify-icon icon="solar:alt-arrow-down-linear" className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"></iconify-icon>
                </div>
            </div>
            <div className="space-y-1.5">
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Siklus Pembayaran</label>
                <div className="relative">
                    <select 
                        value={billingCycle} 
                        onChange={e => setBillingCycle(e.target.value)} 
                        className="w-full pl-4 pr-10 py-3.5 rounded-xl border border-zinc-700 bg-zinc-950 text-white text-sm outline-none focus:border-orange-500 appearance-none transition-colors"
                    >
                        <option value="Monthly">Bulanan (Monthly)</option>
                        <option value="Yearly">Tahunan (Yearly)</option>
                    </select>
                    <iconify-icon icon="solar:alt-arrow-down-linear" className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"></iconify-icon>
                </div>
            </div>
        </div>

        {/* === PRICE PREVIEW CARD === */}
        {(() => {
          const planData = plans.find(p => p.id === selectedPlan);
          if (!planData) return null;
          const amount = billingCycle === 'Monthly' ? planData.monthly : planData.yearly;
          const formatIDR = (val) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(val);
          const cycleLabel = billingCycle === 'Monthly' ? 'bulan' : 'tahun';
          const yearlySavings = billingCycle === 'Yearly' ? Math.round(((planData.monthly * 12) - planData.yearly) / (planData.monthly * 12) * 100) : 0;

          return (
            <div className="bg-zinc-950 border border-zinc-700 rounded-2xl p-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in duration-300">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center shrink-0">
                  <iconify-icon icon="solar:wallet-money-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-0.5">Total Tagihan</p>
                  <p className="text-2xl font-black text-white tracking-tight">{formatIDR(amount)}</p>
                  <p className="text-[10px] text-zinc-500 mt-0.5">
                    {planData.name} · {billingCycle === 'Monthly' ? 'Bulanan' : 'Tahunan'}
                    {billingCycle === 'Yearly' && (
                      <span className="ml-2 text-emerald-400 font-bold">Hemat {yearlySavings}% vs Bulanan</span>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-zinc-500">Per {cycleLabel}</p>
                <p className="text-xs font-bold text-zinc-300 mt-0.5">{formatIDR(billingCycle === 'Monthly' ? amount : Math.round(amount / 12))}/bln</p>
              </div>
            </div>
          );
        })()}
        {/* === END PRICE PREVIEW CARD === */}

        <div className="flex justify-end pt-4 border-t border-zinc-800">
            <button 
                onClick={handlePay}
                disabled={loading}
                className="w-full md:w-auto px-8 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-xl font-bold transition-all shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group"
            >
                {loading ? (
                    <iconify-icon icon="line-md:loading-twotone-loop" className="text-xl"></iconify-icon>
                ) : (
                    <iconify-icon icon="solar:wallet-bold" className="text-xl group-hover:scale-110 transition-transform"></iconify-icon>
                )}
                {clientData?.status === 'expired' ? 'Bayar Tagihan Sekarang' : 'Lanjutkan Pembayaran'}
            </button>
        </div>
      </div>

    </div>
  );
};

export default BillingTab;
