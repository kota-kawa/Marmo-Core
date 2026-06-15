import React from 'react';

const PartnerReviewModal = ({ 
  selectedPartnerApp, 
  setSelectedPartnerApp, 
  setShowApproveModal,
  handleOpenApproveModal
}) => {
  if (!selectedPartnerApp) return null;

  const handleLanjutApprove = () => {
    // Tutup review modal dulu, lalu buka AccountSetupModal via handleOpenApproveModal
    // agar password ter-generate dengan benar
    setSelectedPartnerApp(null);
    if (handleOpenApproveModal) {
      handleOpenApproveModal(selectedPartnerApp);
    } else {
      setShowApproveModal(true);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center p-6 animate-in fade-in duration-300">
      <div className="bg-zinc-900 border border-zinc-800 w-full max-w-xl rounded-3xl overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300">
        <div className="p-8 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/50">
          <div>
            <h2 className="text-xl font-black text-white uppercase tracking-tight">Review Strategi Partner</h2>
            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mt-1">ID: {selectedPartnerApp.id}</p>
          </div>
          <button onClick={() => setSelectedPartnerApp(null)} className="text-zinc-500 hover:text-white">
            <iconify-icon icon="solar:close-circle-bold" className="text-3xl"></iconify-icon>
          </button>
        </div>
        <div className="p-8 space-y-6 max-h-[60vh] overflow-y-auto custom-scrollbar">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-1">Nama Partner</p>
              <p className="text-white font-bold">{selectedPartnerApp.nama}</p>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-1">Email</p>
              <div className="flex items-center gap-2">
                <p className="text-white font-bold">{selectedPartnerApp.email}</p>
                {selectedPartnerApp.email && (
                  <a href={`mailto:${selectedPartnerApp.email}`} className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[8px] font-black uppercase rounded-md border border-blue-500/20 hover:bg-blue-500/20 transition-all">Kirim</a>
                )}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-1">WhatsApp / No. HP</p>
              {selectedPartnerApp.whatsapp || selectedPartnerApp.phone ? (
                <div className="flex items-center gap-2">
                  <p className="text-white font-bold">{selectedPartnerApp.whatsapp || selectedPartnerApp.phone}</p>
                  {(() => {
                    const raw = (selectedPartnerApp.whatsapp || selectedPartnerApp.phone || '').replace(/\D/g, '').replace(/^0/, '62');
                    return raw ? (
                      <a href={`https://wa.me/${raw}`} target="_blank" rel="noopener noreferrer" className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[8px] font-black uppercase rounded-md border border-emerald-500/20 hover:bg-emerald-500/20 transition-all">Chat WA</a>
                    ) : null;
                  })()}
                </div>
              ) : (
                <p className="text-zinc-600 italic text-xs">Tidak tersedia</p>
              )}
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-1">Niche</p>
              <p className="text-amber-500 font-black uppercase">{selectedPartnerApp.niche}</p>
            </div>
            <div>
              <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-1">Followers</p>
              <p className="text-white font-bold">{selectedPartnerApp.followers}</p>
            </div>
          </div>
          
          <div>
            <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-2">Metode Promosi</p>
            <div className="flex flex-wrap gap-2">
              {selectedPartnerApp.promo_methods?.map((m, i) => (
                <span key={i} className="px-3 py-1 bg-zinc-800 text-zinc-300 text-[10px] font-black uppercase rounded-lg border border-zinc-700">{m}</span>
              ))}
            </div>
          </div>

          <div className="p-6 bg-zinc-950 rounded-2xl border border-zinc-800">
            <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-3 flex items-center gap-2">
              <iconify-icon icon="solar:lightbulb-bold-duotone"></iconify-icon>
              Strategi Promosi
            </p>
            <p className="text-zinc-400 text-sm leading-relaxed italic">"{selectedPartnerApp.promo_strategy}"</p>
          </div>
        </div>
        <div className="p-8 border-t border-zinc-800 bg-zinc-950/50 flex justify-end gap-4">
          <button onClick={() => setSelectedPartnerApp(null)} className="px-6 py-3 text-zinc-500 font-black uppercase text-[10px] tracking-widest hover:text-white transition-colors">Tutup</button>
          <button 
            onClick={handleLanjutApprove}
            className="px-8 py-3 bg-amber-600 text-white font-black uppercase text-[10px] tracking-widest rounded-2xl hover:bg-amber-500 transition-all shadow-xl shadow-amber-600/20"
          >
            Lanjut Approve
          </button>
        </div>
      </div>
    </div>
  );
};

export default PartnerReviewModal;
