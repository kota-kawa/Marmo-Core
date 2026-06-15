import React, { useState } from 'react';
import { supabase } from '../../../lib/supabase.js';

const PartnerSection = ({ 
  t, 
  adminPartners = [], 
  adminClients = [],
  globalStats = {},
  getTierBadgeClass,
  fetchPartners
}) => {
  const [selectedPartner, setSelectedPartner] = useState(null);

  // Hitung total referral riil dari jumlah klien yang memiliki partner
  const realTotalReferrals = adminClients.filter(c => c.partners).length;

  const handleSuspend = async () => {
    if (!selectedPartner) return;
    if (!window.confirm(`Yakin ingin memblokir ${selectedPartner.full_name}?`)) return;
    
    const { error } = await supabase.from('partners').update({ status: 'suspended' }).eq('id', selectedPartner.id);
    if (error) {
      alert("Gagal memblokir: " + error.message);
    } else {
      alert("Partner berhasil diblokir!");
      setSelectedPartner(null);
      if (fetchPartners) fetchPartners();
    }
  };

  const handleUpdateTier = async () => {
    if (!selectedPartner) return;
    const newTier = window.prompt(`Masukkan Tier Baru untuk ${selectedPartner.full_name}\n(Bronze / Silver / Gold / Platinum):`);
    if (!newTier) return;
    
    const validTiers = ['bronze', 'silver', 'gold', 'platinum'];
    if (!validTiers.includes(newTier.toLowerCase())) {
      alert("Tier tidak valid!");
      return;
    }

    const { error } = await supabase.from('partners').update({ tier: newTier.toLowerCase() }).eq('id', selectedPartner.id);
    if (error) {
      alert("Gagal mengubah tier: " + error.message);
    } else {
      alert("Tier berhasil diubah!");
      setSelectedPartner(null);
      if (fetchPartners) fetchPartners();
    }
  };

  const handleViewDetail = () => {
    if (!selectedPartner) return;
    const myClients = adminClients.filter(c => c.partner_id === selectedPartner.id || c.ref === selectedPartner.full_name);
    
    if (myClients.length === 0) {
      alert(`Partner ${selectedPartner.full_name} belum memiliki referral.`);
      return;
    }

    const clientList = myClients.map(c => `- ${c.shop_name || c.email} (${c.plan || 'starter'})`).join('\n');
    alert(`Daftar Referral untuk ${selectedPartner.full_name}:\n\n${clientList}`);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800">
           <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">{t('totalReferrals')}</p>
           <h3 className="text-3xl font-black text-white tracking-tighter">{realTotalReferrals}</h3>
        </div>
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800">
           <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">{t('networkPayouts')}</p>
           <h3 className="text-3xl font-black text-green-500 tracking-tighter">Rp {new Intl.NumberFormat('id-ID').format(globalStats.totalPaid || 0)}</h3>
        </div>
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800">
           <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">ACTIVE PARTNERS</p>
           <h3 className="text-3xl font-black text-amber-500 tracking-tighter">{adminPartners.length}</h3>
        </div>
      </div>

      <div className="bg-zinc-900/50 rounded-[2.5rem] border border-zinc-800 overflow-hidden shadow-2xl">
        <div className="p-8 border-b border-zinc-800 bg-zinc-950/50 flex justify-between items-center">
          <div>
            <h3 className="font-black text-white uppercase tracking-tight">{t('globalNetwork')}</h3>
            <p className="text-xs text-zinc-500 font-medium">Managing affiliates, agencies, and content creators</p>
          </div>
        </div>
        <div className="p-8 overflow-x-auto custom-scrollbar">
          <table className="w-full text-left border-separate border-spacing-y-2 min-w-[1000px]">
            <thead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">
              <tr>
                <th className="px-4 pb-2">{t('partnerEntity')}</th>
                <th className="px-4 pb-2">CONTACT</th>
                <th className="px-4 pb-2 text-center">{t('tier')}</th>
                <th className="px-4 pb-2 text-right">{t('referrals')}</th>
                <th className="px-4 pb-2 text-center">{t('status')}</th>
                <th className="px-4 pb-2 text-right">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {adminPartners.length > 0 ? adminPartners.map((p) => (
                <tr key={p.id} className="bg-zinc-950/50 hover:bg-zinc-800/50 transition-all group">
                  <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800">
                    <div className="font-black text-white text-sm tracking-tight">{p.full_name}</div>
                    <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest opacity-60">REF: {p.affiliate_id || 'N/A'}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800">
                     <div className="text-[10px] font-black text-white uppercase mb-1">{p.email}</div>
                     <div className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest">{p.whatsapp || 'No WhatsApp'}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                     <span className={`${getTierBadgeClass(p.tier)} text-[8px] font-black px-3 py-1 rounded-lg tracking-widest uppercase`}>{p.tier || 'Bronze'}</span>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-right font-black text-white text-sm">
                    {adminClients.filter(c => c.partner_id === p.id || c.ref === p.full_name).length}
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                    <span className={`text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border ${p.status === 'active' ? 'text-green-500 border-green-500/20' : 'text-amber-500 border-amber-500/20'}`}>{p.status?.toUpperCase() || 'ACTIVE'}</span>
                  </td>
                  <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800 text-right">
                     <div className="flex items-center justify-end gap-2">
                       <button onClick={() => setSelectedPartner(p)} className="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-white hover:text-black rounded-xl border border-zinc-700 transition-all">
                         <iconify-icon icon="solar:settings-bold-duotone" className="text-xl"></iconify-icon>
                       </button>
                     </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" className="py-20 text-center text-zinc-600 italic text-sm">No partners found in database.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Glassmorphism Pop-up */}
      {selectedPartner && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-md z-[100] flex items-center justify-center p-4 animate-in fade-in duration-300">
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-[2rem] p-8 w-full max-w-md shadow-2xl shadow-black/50 text-white relative">
            <button 
              onClick={() => setSelectedPartner(null)} 
              className="absolute top-6 right-6 text-white/60 hover:text-white transition-colors"
            >
              <iconify-icon icon="solar:close-circle-bold-duotone" className="text-2xl"></iconify-icon>
            </button>
            
            <div className="mb-6">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">Aksi Partner</span>
              <h3 className="text-2xl font-black tracking-tight mt-1">{selectedPartner.full_name}</h3>
              <p className="text-xs text-white/60 mt-1">{selectedPartner.email}</p>
              {/* WhatsApp / No. HP */}
              {selectedPartner.whatsapp ? (
                <div className="flex items-center gap-2 mt-2">
                  <iconify-icon icon="solar:phone-bold-duotone" className="text-sm text-emerald-400"></iconify-icon>
                  <span className="text-xs text-white/80 font-bold">{selectedPartner.whatsapp}</span>
                  {(() => {
                    const raw = selectedPartner.whatsapp.replace(/\D/g, '').replace(/^0/, '62');
                    return raw ? (
                      <a
                        href={`https://wa.me/${raw}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[8px] font-black uppercase rounded-md border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
                      >
                        Chat WA
                      </a>
                    ) : null;
                  })()}
                </div>
              ) : (
                <p className="text-xs text-white/30 mt-2 italic">No. WA tidak tersedia</p>
              )}
            </div>

            <div className="space-y-3">
              <button onClick={handleViewDetail} className="w-full flex items-center gap-3 p-4 bg-white/5 hover:bg-white/20 rounded-xl border border-white/10 transition-all group">
                <iconify-icon icon="solar:eye-bold-duotone" className="text-xl text-blue-400 group-hover:scale-110 transition-transform"></iconify-icon>
                <div className="text-left">
                  <p className="text-xs font-black uppercase tracking-wider">Lihat Detail / Aktivitas</p>
                  <p className="text-[10px] text-white/40">Lihat performa & klien partner ini</p>
                </div>
              </button>

              <button onClick={handleUpdateTier} className="w-full flex items-center gap-3 p-4 bg-white/5 hover:bg-white/20 rounded-xl border border-white/10 transition-all group">
                <iconify-icon icon="solar:medal-star-bold-duotone" className="text-xl text-amber-400 group-hover:scale-110 transition-transform"></iconify-icon>
                <div className="text-left">
                  <p className="text-xs font-black uppercase tracking-wider">Ubah Tier Manual</p>
                  <p className="text-[10px] text-white/40">Naikkan pangkat ke Gold/Platinum</p>
                </div>
              </button>

              <div className="h-px bg-white/10 my-2"></div>

              <button onClick={handleSuspend} className="w-full flex items-center gap-3 p-4 bg-red-500/20 hover:bg-red-500/40 rounded-xl border border-red-500/20 transition-all group">
                <iconify-icon icon="solar:shield-warning-bold-duotone" className="text-xl text-red-400 group-hover:scale-110 transition-transform"></iconify-icon>
                <div className="text-left">
                  <p className="text-xs font-black uppercase tracking-wider text-red-400">Suspend / Blokir</p>
                  <p className="text-[10px] text-red-400/60">Nonaktifkan akses partner ini</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PartnerSection;
