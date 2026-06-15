import React from 'react';

const AiGeneratorTab = ({ 
  t, 
  aiSubTab, 
  setAiSubTab, 
  setAiResult, 
  aiPrompt, 
  setAiPrompt, 
  aiFormat, 
  setAiFormat, 
  isGenerating, 
  handleGenerateAI, 
  aiResult,
  profile
}) => {
  const isStarter = profile && (profile?.subscription_plan || 'starter').toLowerCase() === 'starter';
  return (
    <div className="relative z-10">
      {/* Header */}
      <header className="mb-6">
        <h2 className="text-2xl font-semibold text-white tracking-tight flex items-center gap-2">
          {t('aiGenerator')}
        </h2>
        <p className="text-sm text-zinc-400 mt-1">{t('aiDesc')}</p>
      </header>

      {/* Sub-tab: Content only — Trend Radar moved to Market Intel */}
      <div className="flex gap-2 mb-8 bg-black border border-zinc-800 rounded-xl p-1 w-fit">
        <button
          onClick={() => { setAiSubTab('content'); setAiResult(''); }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all bg-orange-600 text-white shadow-md"
        >
          <iconify-icon icon="solar:magic-stick-3-linear" className="text-base"></iconify-icon>
          {t('contentGen')}
        </button>
      </div>

      {/* === SUB-TAB: CONTENT GENERATOR === */}
      {aiSubTab === 'content' && (
        <div className="max-w-2xl space-y-6">
          <div className="space-y-1">
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-widest">{t('prodDesc')}</label>
            <div className={`relative bg-black border rounded-xl shadow-sm transition duration-300 ${isGenerating ? 'border-zinc-700 opacity-60' : 'border-zinc-800 focus-within:border-orange-500 focus-within:ring-1 focus-within:ring-orange-500/50'}`}>
              <textarea
                className="w-full bg-transparent p-4 text-sm text-white focus:outline-none placeholder:text-zinc-600 resize-none disabled:cursor-not-allowed"
                rows="4"
                placeholder={t('aiPromptPlaceholder')}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                disabled={isGenerating}
              ></textarea>
            </div>
          </div>

          <div className="space-y-4">
            <label className="block text-xs font-medium text-zinc-500 uppercase tracking-widest mb-1">{t('formatOutput')}</label>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Video Content Group */}
              <div className={`p-4 rounded-2xl border transition-all relative overflow-hidden ${isStarter ? 'opacity-45 border-zinc-800/80 bg-zinc-950/20 cursor-not-allowed select-none' : aiFormat.includes('Video') ? 'bg-orange-950/20 border-orange-500/50' : 'bg-black border-zinc-800'}`}>
                {isStarter && (
                  <div className="absolute inset-0 bg-black/70 backdrop-blur-[2px] z-10 flex flex-col items-center justify-center text-center p-3">
                    <div className="w-8 h-8 bg-amber-500/10 rounded-lg flex items-center justify-center mb-1 border border-amber-500/20">
                      <iconify-icon icon="solar:lock-keyhole-bold-duotone" className="text-base text-amber-500"></iconify-icon>
                    </div>
                    <span className="text-[9px] font-black tracking-widest text-amber-400 uppercase">PRO PLAN ONLY</span>
                    <p className="text-[7px] text-zinc-500 leading-tight mt-0.5 max-w-[120px]">Upgrade to PRO to unlock AI Video Scripts</p>
                  </div>
                )}
                <div className="flex items-center gap-2 mb-3">
                  <iconify-icon icon="solar:video-frame-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
                  <span className="text-xs font-bold text-white uppercase tracking-wider">{t('videoContent')}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {['TikTok Video', 'Instagram Reels'].map(f => (
                    <button
                      key={f}
                      onClick={() => !isStarter && setAiFormat(f)}
                      disabled={isStarter}
                      className={`px-3 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all text-left flex items-center justify-between ${aiFormat === f ? 'bg-orange-600 text-white' : 'bg-zinc-900 text-zinc-500 hover:text-zinc-300'} ${isStarter ? 'pointer-events-none' : ''}`}
                    >
                      {f}
                      {aiFormat === f && <iconify-icon icon="solar:check-circle-bold"></iconify-icon>}
                    </button>
                  ))}
                </div>
              </div>

              {/* Text Content Group */}
              <div className={`p-4 rounded-2xl border transition-all ${!aiFormat.includes('Video') ? 'bg-orange-950/20 border-orange-500/50' : 'bg-black border-zinc-800'}`}>
                <div className="flex items-center gap-2 mb-3">
                  <iconify-icon icon="solar:notes-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
                  <div>
                    <span className="text-xs font-bold text-white uppercase tracking-wider block">{t('textContent')}</span>
                    <span className="text-[9px] text-zinc-500 italic block">(Product Name & Description)</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  {['Shopee Description', 'Tokopedia Description', 'TikTok Shop Description'].filter(f => f !== 'Tokopedia Description').map(f => (
                    <button
                      key={f}
                      onClick={() => setAiFormat(f)}
                      className={`px-3 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all text-left flex items-center justify-between ${aiFormat === f ? 'bg-orange-600 text-white' : 'bg-zinc-900 text-zinc-500 hover:text-zinc-300'}`}
                    >
                      {f}
                      {aiFormat === f && <iconify-icon icon="solar:check-circle-bold"></iconify-icon>}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleGenerateAI}
            disabled={isGenerating || !aiPrompt}
            className="w-full bg-orange-600 text-white py-3.5 rounded-xl text-sm font-bold shadow-md hover:bg-orange-500 transition-all flex justify-center items-center gap-2 border border-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <><iconify-icon icon="solar:spinner-linear" className="text-lg animate-spin"></iconify-icon> {t('genLoading')}</>
            ) : (
              <><iconify-icon icon="solar:stars-bold" className="text-lg"></iconify-icon> Surprise Me!!!</>
            )}
          </button>

          {aiResult && (
            <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-xl relative group">
              <button
                onClick={() => navigator.clipboard.writeText(aiResult)}
                className="absolute top-4 right-4 text-zinc-500 hover:text-orange-500 transition-colors opacity-0 group-hover:opacity-100 p-2 bg-black rounded-md border border-zinc-800"
              >
                <iconify-icon icon="solar:copy-linear" className="text-lg"></iconify-icon>
              </button>
              <div className="flex items-center gap-2 mb-4 text-orange-500 text-xs font-medium uppercase tracking-widest">
                <iconify-icon icon="solar:check-circle-linear" className="text-base"></iconify-icon>
                {t('genResult')}
              </div>
              <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{aiResult}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AiGeneratorTab;
