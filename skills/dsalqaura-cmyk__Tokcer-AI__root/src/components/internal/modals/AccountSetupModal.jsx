import React from 'react';

const AccountSetupModal = ({ 
  showApproveModal, 
  setShowApproveModal, 
  selectedPartnerApp, 
  generatedPassword,
  setApprovalAccount, 
  handleApproveWithAccount, 
  isLoading 
}) => {
  if (!showApproveModal || !selectedPartnerApp) return null;


  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-xl z-[110] flex items-center justify-center p-6 animate-in fade-in duration-300">
      <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-[2.5rem] overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300">
        <div className="p-10 text-center border-b border-zinc-800 bg-zinc-950/50">
          <div className="w-20 h-20 bg-amber-500/10 text-amber-500 rounded-full flex items-center justify-center mx-auto mb-6 border-2 border-amber-500/20">
            <iconify-icon icon="solar:shield-user-bold-duotone" className="text-4xl"></iconify-icon>
          </div>
          <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Setup Akun Partner</h2>
          <p className="text-zinc-500 text-xs mt-2 font-medium">Berikan akses Dashboard User dengan Tier Ultimate 60 Hari</p>
        </div>
        <div className="p-10 space-y-6">
          <div className="space-y-4">
            <div className="bg-black/40 border border-zinc-800/50 rounded-2xl p-5 flex items-center justify-between">
              <div>
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1 block">Username Dashboard</label>
                <div className="text-sm text-white font-medium">{selectedPartnerApp.email}</div>
              </div>
              <iconify-icon icon="solar:user-bold" className="text-zinc-700 text-xl"></iconify-icon>
            </div>
            
            <div className="bg-black/40 border border-zinc-800/50 rounded-2xl p-5 flex items-center justify-between">
              <div>
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1 block">Password Sementara</label>
                <div className="text-sm text-amber-500 font-mono font-bold tracking-wider">{generatedPassword}</div>
              </div>
              <iconify-icon icon="solar:lock-password-bold" className="text-zinc-700 text-xl"></iconify-icon>
            </div>
          </div>

          <div className="bg-amber-600/5 border border-amber-600/20 p-5 rounded-2xl flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
              <iconify-icon icon="solar:info-circle-bold" className="text-amber-500 text-sm"></iconify-icon>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed font-medium">
              Akun akan otomatis dibuatkan di sistem. Detail login akan dikirim ke email <span className="font-bold text-white">{selectedPartnerApp.email}</span> setelah Bapak menekan tombol di bawah.
            </p>
          </div>
        </div>
        <div className="p-10 bg-zinc-950/50 flex flex-col gap-3">
          <button 
            onClick={handleApproveWithAccount}
            disabled={isLoading}
            className="group relative w-full py-5 bg-amber-600 text-white font-black uppercase text-xs tracking-[0.2em] rounded-2xl hover:bg-amber-500 transition-all shadow-2xl shadow-amber-600/20 active:scale-95 disabled:opacity-50 overflow-hidden"
          >
            <span className="relative z-10">{isLoading ? 'MEMPROSES...' : 'AKTIFKAN & KIRIM EMAIL'}</span>
            {!isLoading && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>}
          </button>
          
          <button onClick={() => setShowApproveModal(false)} className="w-full py-4 text-zinc-500 font-black uppercase text-[10px] tracking-widest hover:text-white transition-colors">Batal</button>


        </div>
      </div>
    </div>
  );
};

export default AccountSetupModal;
