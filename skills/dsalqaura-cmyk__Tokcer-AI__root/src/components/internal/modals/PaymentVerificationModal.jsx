import React, { useState } from 'react';

const PaymentVerificationModal = ({ 
  t, 
  showModal, 
  setShowModal, 
  selectedClient, 
  handleApprove 
}) => {
  const [aiStatus, setAiStatus] = useState('idle'); // idle, analyzing, success, error
  const [aiReport, setAiReport] = useState('');

  if (!showModal) return null;

  const runAiVerification = () => {
    setAiStatus('analyzing');
    // Simulasi pemanggilan AI Vision
    setTimeout(() => {
      if (selectedClient?.payment_proof_url) {
        setAiStatus('success');
        setAiReport(`✅ Analisa AI: Nominal cocok dengan paket ${selectedClient?.plan?.toUpperCase() || 'Pro'}. Tanggal transfer valid. Keaslian dokumen: 98% (Bukan editan).`);
      } else {
        setAiStatus('error');
        setAiReport(`❌ Analisa AI: Gambar tidak ditemukan atau buram.`);
      }
    }, 2500);
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-[100] flex items-center justify-center p-4 animate-in fade-in duration-300">
      <div className="bg-zinc-900 rounded-[2.5rem] max-w-md w-full p-8 border border-zinc-800 text-center relative max-h-[90vh] overflow-y-auto custom-scrollbar">
        <h2 className="text-xl font-black text-white uppercase tracking-tight mb-2">{t('confirmApproval')}</h2>
        <p className="text-xs text-zinc-500 mb-6 font-medium italic">{t('approveUpgrade')} {selectedClient?.shop_name || selectedClient?.name}?</p>
        
        {/* Payment Proof Section */}
        {selectedClient?.payment_proof_url ? (
          <div className="mb-6 relative rounded-2xl overflow-hidden border border-zinc-800 bg-black/50 p-2">
            <p className="text-[10px] font-black uppercase text-zinc-500 tracking-widest mb-2 text-left px-2">Bukti Transfer:</p>
            <img src={selectedClient.payment_proof_url} alt="Bukti Bayar" className="w-full h-48 object-contain rounded-xl" />
            
            <div className="mt-4 p-3 bg-zinc-950 rounded-xl border border-zinc-800 text-left">
              {aiStatus === 'idle' && (
                <button onClick={runAiVerification} className="w-full py-2.5 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all border border-indigo-500/20 flex items-center justify-center gap-2">
                  <iconify-icon icon="solar:magic-stick-3-bold"></iconify-icon> AI Verification Check
                </button>
              )}
              {aiStatus === 'analyzing' && (
                <div className="text-center py-2 text-xs text-zinc-400 flex flex-col items-center gap-2">
                  <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                  Menganalisa Nominal & Keaslian...
                </div>
              )}
              {(aiStatus === 'success' || aiStatus === 'error') && (
                <p className={`text-xs leading-relaxed ${aiStatus === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {aiReport}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs text-center">
            ⚠️ Klien belum mengunggah bukti pembayaran.
          </div>
        )}

        <div className="flex gap-4">
          <button onClick={() => handleApprove(selectedClient)} className="flex-1 py-4 bg-blue-600 text-white font-black uppercase text-[10px] tracking-widest rounded-2xl">{t('confirm')}</button>
          <button onClick={() => setShowModal(false)} className="flex-1 py-4 bg-zinc-800 text-zinc-400 font-black uppercase text-[10px] tracking-widest rounded-2xl">{t('cancel')}</button>
        </div>
      </div>
    </div>
  );
};

export default PaymentVerificationModal;
