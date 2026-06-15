import React from 'react';

const AcademyTab = ({ 
  t 
}) => {
  const academyItems = [
    { title: 'ClosingMastery', icon: 'solar:videocamera-record-bold-duotone', color: 'text-orange-500', bg: 'bg-orange-500/10' },
    { title: 'ContentBank', icon: 'solar:gallery-bold-duotone', color: 'text-orange-500', bg: 'bg-orange-500/10' },
    { title: 'AdsFramework', icon: 'solar:graph-bold-duotone', color: 'text-orange-500', bg: 'bg-orange-500/10' },
    { title: 'ProductKnowledge', icon: 'solar:reorder-bold-duotone', color: 'text-orange-500', bg: 'bg-orange-500/10' }
  ];

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
      <div className="text-center space-y-3">
        <h2 className="text-2xl font-black text-white uppercase tracking-[0.4em]">{t('academyTitle')}</h2>
        <p className="text-xs font-bold text-zinc-400 uppercase tracking-[0.2em]">{t('academyDesc')}</p>
      </div>

      {/* Partner Guide Download Card */}
      <div className="bg-gradient-to-r from-orange-600/10 via-amber-600/5 to-transparent border border-orange-500/20 rounded-[32px] p-8 md:p-10 flex flex-col md:flex-row items-center justify-between gap-8 shadow-xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-orange-600/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
        <div className="flex items-center gap-6 relative z-10">
          <div className="w-16 h-16 bg-orange-500/20 rounded-2xl flex items-center justify-center border border-orange-500/30 shrink-0 group-hover:scale-110 transition-transform">
            <iconify-icon icon="solar:document-bold-duotone" className="text-4xl text-orange-500"></iconify-icon>
          </div>
          <div className="space-y-2 text-center md:text-left">
            <h3 className="text-white font-black text-lg uppercase tracking-wider">{t('academyGuideDownloadTitle')}</h3>
            <p className="text-zinc-400 text-xs max-w-2xl leading-relaxed">
              {t('academyGuideDownloadDesc')}
            </p>
          </div>
        </div>
        <div className="relative z-10 w-full md:w-auto flex justify-center shrink-0">
          <a 
            href="/Tokcer_AI_Partner_Guide.pdf"
            download="Tokcer_AI_Partner_Guide.pdf"
            className="w-full md:w-auto bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold uppercase tracking-widest px-8 py-3.5 rounded-xl shadow-lg shadow-orange-500/20 hover:shadow-orange-500/40 transition-all duration-300 hover:scale-[1.02] flex items-center justify-center gap-2"
          >
            <iconify-icon icon="solar:download-minimalistic-bold" className="text-lg"></iconify-icon>
            {t('academyGuideDownloadBtn')}
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {academyItems.map((item, idx) => (
          <div key={idx} className="group bg-zinc-900/40 backdrop-blur-md border border-zinc-800/50 p-8 rounded-[32px] cursor-not-allowed opacity-70">
            <div className={`w-14 h-14 ${item.bg} rounded-2xl flex items-center justify-center mb-6 grayscale opacity-50`}>
              <iconify-icon icon={item.icon} className={`text-3xl ${item.color}`}></iconify-icon>
            </div>
            <h3 className="text-sm font-black text-white uppercase tracking-widest mb-2">{t('academy' + item.title)}</h3>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest leading-relaxed mb-6">{t('academy' + item.title + 'Desc')}</p>
            <div className="flex items-center gap-2 text-[9px] font-black text-zinc-600 uppercase tracking-[0.2em]">
              <iconify-icon icon="solar:lock-bold"></iconify-icon> COMING SOON
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AcademyTab;
