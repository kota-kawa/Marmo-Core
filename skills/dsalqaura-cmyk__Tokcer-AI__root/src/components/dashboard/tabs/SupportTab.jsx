import React, { useState } from 'react';

const SupportTab = ({ 
  t, 
  lang,
  supportSubmitted, 
  setSupportSubmitted, 
  setActiveMenu, 
  supportType, 
  setSupportType, 
  handleSupportSubmit, 
  supportTitle, 
  setSupportTitle, 
  supportDesc, 
  setSupportDesc, 
  supportFile, 
  handleFileChange, 
  supportFilePreview, 
  setSupportFile, 
  setSupportFilePreview, 
  isSubmittingSupport,
  userTickets = [],
  isFetchingUserTickets = false
}) => {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const categories = [
    { id: 'all', label: lang === 'id' ? 'Semua' : 'All', icon: 'solar:widget-linear' },
    { id: 'general', label: lang === 'id' ? 'Umum' : 'General', icon: 'solar:info-circle-linear' },
    { id: 'billing', label: lang === 'id' ? 'Pembayaran' : 'Billing', icon: 'solar:wallet-money-linear' },
    { id: 'technical', label: lang === 'id' ? 'Teknis' : 'Technical', icon: 'solar:settings-linear' },
    { id: 'account', label: lang === 'id' ? 'Akun' : 'Account', icon: 'solar:user-circle-linear' },
  ];

  const faqs = [
    { q: lang === 'id' ? 'Bagaimana cara menghubungkan toko TikTok?' : 'How to connect TikTok shop?', a: lang === 'id' ? 'Buka tab Integrasi, pilih TikTok, dan ikuti instruksi login oAuth.' : 'Go to Integration tab, select TikTok, and follow oAuth login instructions.', cat: 'technical' },
    { q: lang === 'id' ? 'Kapan omzet saya diperbarui?' : 'When is my revenue updated?', a: lang === 'id' ? 'Data diperbarui secara real-time setiap ada transaksi masuk dari platform.' : 'Data is updated in real-time for every incoming transaction from platforms.', cat: 'general' },
    { q: lang === 'id' ? 'Apakah data saya aman?' : 'Is my data secure?', a: lang === 'id' ? 'Ya, kami menggunakan enkripsi tingkat tinggi dan tidak menyimpan password toko Anda.' : 'Yes, we use high-level encryption and do not store your shop passwords.', cat: 'account' },
    { q: lang === 'id' ? 'Metode pembayaran apa yang tersedia?' : 'What payment methods are available?', a: lang === 'id' ? 'Kami mendukung Virtual Account, E-Wallet (OVO, Dana), dan Kartu Kredit.' : 'We support Virtual Account, E-Wallet (OVO, Dana), and Credit Cards.', cat: 'billing' },
  ];

  const filteredFaqs = faqs.filter(f => 
    (activeCategory === 'all' || f.cat === activeCategory) &&
    (f.q.toLowerCase().includes(searchQuery.toLowerCase()) || f.a.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (supportSubmitted) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in zoom-in duration-500">
        <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 border border-emerald-500/20">
          <iconify-icon icon="solar:check-circle-bold" className="text-5xl text-emerald-500"></iconify-icon>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">{t('supportSuccess')}</h2>
        <p className="text-zinc-400 max-w-sm mb-8">{t('supportSuccessDesc')}</p>
        <button 
          onClick={() => { setSupportSubmitted(false); setActiveMenu('tab-dash'); }}
          className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all"
        >
          {t('backToDashboard')}
        </button>
      </div>
    );
  }

  return (
    <div className="relative z-10 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-4">
        <h2 className="text-2xl font-semibold text-white tracking-tight">{t('supportCenter')}</h2>
        <p className="text-xs text-zinc-400 mt-1">{lang === 'id' ? 'Laporkan kendala teknis atau ajukan usulan fitur baru langsung ke tim developer kami.' : 'Report technical bugs or suggest new features directly to our developer team.'}</p>
      </header>

      {/* Bug & Feature Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Bug Report Option */}
        <div 
          onClick={() => setSupportType('bug')}
          className={`cursor-pointer p-6 rounded-2xl border transition-all ${supportType === 'bug' ? 'bg-orange-950/20 border-orange-500 shadow-[0_0_20px_rgba(249,115,22,0.1)]' : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'}`}
        >
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${supportType === 'bug' ? 'bg-orange-600 text-white' : 'bg-zinc-800 text-zinc-400'}`}>
            <iconify-icon icon="solar:danger-bold" className="text-2xl"></iconify-icon>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">{t('reportBug')}</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">{t('bugDesc')}</p>
        </div>

        {/* Feature Suggestion Option */}
        <div 
          onClick={() => setSupportType('feature')}
          className={`cursor-pointer p-6 rounded-2xl border transition-all ${supportType === 'feature' ? 'bg-orange-950/20 border-orange-500 shadow-[0_0_20px_rgba(249,115,22,0.1)]' : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'}`}
        >
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${supportType === 'feature' ? 'bg-orange-600 text-white' : 'bg-zinc-800 text-zinc-400'}`}>
            <iconify-icon icon="solar:lightbulb-bold" className="text-2xl"></iconify-icon>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">{t('suggestFeature')}</h3>
          <p className="text-xs text-zinc-500 leading-relaxed">{t('featureDesc')}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-8 mb-4">
        <div className="w-10 h-10 rounded-xl bg-zinc-900 flex items-center justify-center border border-zinc-800">
          <iconify-icon icon="solar:pen-new-square-linear" className="text-xl text-orange-500"></iconify-icon>
        </div>
        <div>
          <h3 className="text-sm font-bold text-white">{t('sendTicket') || (lang === 'id' ? 'Kirim Laporan' : 'Send Ticket')}</h3>
          <p className="text-[10px] text-zinc-500">{t('ticketDesc') || (lang === 'id' ? 'Isi formulir di bawah ini secara lengkap untuk langsung diteruskan ke tim engineering kami.' : 'Fill out the form below to submit directly to our engineering team.')}</p>
        </div>
      </div>

      <form onSubmit={handleSupportSubmit} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 md:p-8 space-y-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500 uppercase tracking-widest mb-2">
              {supportType === 'bug' ? t('bugTitleLabel') : t('featureTitleLabel')}
            </label>
            <input 
              type="text" 
              required
              value={supportTitle}
              onChange={(e) => setSupportTitle(e.target.value)}
              className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500 transition-all placeholder:text-zinc-600"
              placeholder={supportType === 'bug' ? t('bugTitlePlaceholder') : t('featureTitlePlaceholder')}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-500 uppercase tracking-widest mb-2">
              {supportType === 'bug' ? t('bugDetailLabel') : t('featureDetailLabel')}
            </label>
            <textarea 
              required
              rows="5"
              value={supportDesc}
              onChange={(e) => setSupportDesc(e.target.value)}
              className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500 transition-all placeholder:text-zinc-600 resize-none"
              placeholder={supportType === 'bug' ? t('bugDetailPlaceholder') : t('featureDetailPlaceholder')}
            ></textarea>
          </div>

          {supportType === 'bug' && (
            <div>
              <label className="block text-xs font-medium text-zinc-500 uppercase tracking-widest mb-2">
                {t('uploadScreenshot')}
              </label>
              <div className="flex items-center gap-4">
                <label className="cursor-pointer flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-xl text-xs font-medium text-zinc-300 hover:bg-zinc-700 hover:text-white transition-all">
                  <iconify-icon icon="solar:camera-linear" className="text-lg"></iconify-icon>
                  {supportFile ? supportFile.name : t('uploadScreenshot')}
                  <input type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
                </label>
                {supportFilePreview && (
                  <div className="relative w-12 h-12 rounded-lg overflow-hidden border border-zinc-700">
                    <img src={supportFilePreview} alt="Preview" className="w-full h-full object-cover" />
                    <button 
                      type="button"
                      onClick={() => { setSupportFile(null); setSupportFilePreview(null); }}
                      className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
                    >
                      <iconify-icon icon="solar:trash-bin-trash-bold" className="text-white"></iconify-icon>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <button 
          type="submit" 
          disabled={isSubmittingSupport}
          className="w-full bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white py-4 rounded-xl text-sm font-bold shadow-lg transition-all flex items-center justify-center gap-2"
        >
          {isSubmittingSupport ? (
            <><iconify-icon icon="solar:spinner-linear" className="text-xl animate-spin"></iconify-icon> {t('sending')}</>
          ) : (
            <><iconify-icon icon="solar:send-square-bold" className="text-xl"></iconify-icon> {t('sendReport')}</>
          )}
        </button>
      </form>

      {/* 🔽 SECTION RIWAYAT TIKET/LAPORAN USER (ESTETIKA: DI BAWAH TOMBOL KIRIM) 🔽 */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6 md:p-8 shadow-sm">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center border border-orange-500/20">
              <iconify-icon icon="solar:history-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-tight">{lang === 'id' ? 'Status & Riwayat Laporan Anda' : 'Your Ticket Status & History'}</h3>
              <p className="text-[10px] text-zinc-500">{lang === 'id' ? 'Pantau penyelesaian aduan atau request fitur Anda secara real-time.' : 'Monitor the progress of your bug reports or feature requests in real-time.'}</p>
            </div>
          </div>
          <div className="bg-zinc-950 px-3.5 py-1.5 rounded-xl border border-zinc-800/80 flex items-center gap-2">
            <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest">Total: {userTickets?.length || 0}</span>
          </div>
        </div>

        {isFetchingUserTickets ? (
          <div className="py-12 flex flex-col items-center justify-center text-center">
            <iconify-icon icon="solar:spinner-linear" className="text-3xl text-orange-500 animate-spin mb-3"></iconify-icon>
            <p className="text-xs text-zinc-500 font-bold uppercase tracking-wider">{lang === 'id' ? 'Memuat riwayat...' : 'Loading history...'}</p>
          </div>
        ) : userTickets && userTickets.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {userTickets.map((ticket) => (
              <div 
                key={ticket.id} 
                className="bg-zinc-950 p-5 rounded-2xl border border-zinc-850 hover:border-zinc-700 transition-all flex flex-col justify-between gap-4"
              >
                <div>
                  <div className="flex justify-between items-start gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${ticket.type === 'bug' ? 'bg-rose-500 animate-pulse' : 'bg-blue-400'}`}></span>
                      <h4 className="text-xs font-bold text-white uppercase tracking-tight line-clamp-1">{ticket.title}</h4>
                    </div>
                    <span className={`text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-widest shrink-0 ${
                      ticket.status === 'resolved' 
                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' 
                        : ticket.status === 'closed' || ticket.status === 'rejected'
                        ? 'bg-zinc-800 text-zinc-400 border border-zinc-750'
                        : 'bg-amber-500/10 text-amber-500 border border-amber-500/20 animate-pulse'
                    }`}>
                      {ticket.status}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 leading-relaxed line-clamp-2">{ticket.description}</p>
                </div>

                <div className="flex justify-between items-center pt-3 border-t border-zinc-900 text-[9px] font-bold text-zinc-500">
                  <span className="uppercase">TIPE: <span className={ticket.type === 'bug' ? 'text-rose-400' : 'text-blue-400'}>{ticket.type}</span></span>
                  <span>{new Date(ticket.created_at).toLocaleDateString(lang === 'id' ? 'id-ID' : 'en-US', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 flex flex-col items-center justify-center text-center bg-zinc-950/60 rounded-2xl border border-dashed border-zinc-800">
            <iconify-icon icon="solar:notes-linear" className="text-3xl text-zinc-700 mb-3"></iconify-icon>
            <p className="text-xs text-zinc-500 font-medium">{lang === 'id' ? 'Belum ada laporan atau saran yang Anda kirim.' : 'You have not submitted any reports or suggestions yet.'}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SupportTab;
