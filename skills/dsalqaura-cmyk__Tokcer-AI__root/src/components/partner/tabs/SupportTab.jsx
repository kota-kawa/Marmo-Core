import React from 'react';

const SupportTab = ({ 
  t, 
  supportTab, 
  setSupportTab, 
  supportForm, 
  setSupportForm,
  ideaForm,
  setIdeaForm,
  handleSupportSubmit, 
  handleIdeaSubmit,
  isSubmitting
}) => {
  return (
    <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8 pb-20">
      <div className="text-center space-y-4">
        <h2 className="text-3xl font-black text-white uppercase tracking-[0.4em]">{t('supportTitle')}</h2>
        <p className="text-xs font-bold text-zinc-400 uppercase tracking-[0.2em] max-w-lg mx-auto leading-relaxed">{t('supportDesc')}</p>
      </div>

      {/* 🧭 NAVIGATION: Choice between Bug and Feature */}
      <div className="flex justify-center pt-4">
        <div className="flex bg-zinc-900/80 backdrop-blur-xl p-1.5 rounded-[24px] border border-zinc-800 shadow-2xl">
          <button 
            onClick={() => setSupportTab('report')}
            className={`flex items-center gap-2 px-8 py-4 text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all duration-300 ${supportTab === 'report' ? 'bg-orange-600 text-white shadow-[0_0_20px_rgba(234,88,12,0.4)]' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}`}
          >
            <iconify-icon icon="solar:shield-warning-bold-duotone" className="text-lg"></iconify-icon>
            {t('reportBug')}
          </button>
          <button 
            onClick={() => setSupportTab('vision')}
            className={`flex items-center gap-2 px-8 py-4 text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all duration-300 ${supportTab === 'vision' ? 'bg-orange-600 text-white shadow-[0_0_20px_rgba(234,88,12,0.4)]' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}`}
          >
            <iconify-icon icon="solar:lightbulb-bold-duotone" className="text-lg"></iconify-icon>
            {t('suggestFeature')}
          </button>
        </div>
      </div>

      {/* 📝 FORM CONTAINER */}
      <div className="max-w-2xl mx-auto bg-zinc-900/30 backdrop-blur-md border border-zinc-800/50 rounded-[48px] p-8 md:p-14 shadow-2xl relative overflow-hidden group">
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-orange-600 via-amber-500 to-orange-400"></div>
        
        {supportTab === 'report' ? (
          <form className="space-y-10" onSubmit={handleSupportSubmit}>
            <div className="space-y-3">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1 flex items-center gap-2">
                <iconify-icon icon="solar:tag-bold" className="text-orange-500"></iconify-icon>
                {t('category')}
              </label>
              <div className="relative">
                <select 
                  value={supportForm.category}
                  onChange={(e) => setSupportForm({...supportForm, category: e.target.value})}
                  className="w-full appearance-none bg-black/50 border border-zinc-800 focus:border-orange-500/50 rounded-2xl px-6 py-5 text-sm text-white outline-none transition-all"
                >
                  <option value="bug">{t('catBug')}</option>
                  <option value="data">{t('catData')}</option>
                  <option value="login">{t('catLogin')}</option>
                  <option value="commission">{t('catComm')}</option>
                </select>
                <iconify-icon icon="solar:alt-arrow-down-bold" className="absolute right-6 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"></iconify-icon>
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1 flex items-center gap-2">
                <iconify-icon icon="solar:notes-bold" className="text-orange-500"></iconify-icon>
                {t('description')}
              </label>
              <textarea 
                rows="5"
                required
                value={supportForm.description}
                onChange={(e) => setSupportForm({...supportForm, description: e.target.value})}
                className="w-full bg-black/50 border border-zinc-800 focus:border-orange-500/50 rounded-3xl px-6 py-5 text-sm text-white outline-none resize-none transition-all leading-relaxed"
                placeholder={t('descPlaceholder')}
              ></textarea>
            </div>

            <div className="space-y-4">
              <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1">{t('uploadMedia')}</label>
              <div className="relative group/upload">
                <input 
                  type="file" 
                  accept="image/*"
                  onChange={(e) => setSupportForm({...supportForm, screenshot: e.target.files[0]})}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div className="border-2 border-dashed border-zinc-800 group-hover/upload:border-orange-500/30 rounded-[32px] p-12 flex flex-col items-center justify-center transition-all bg-white/[0.01] group-hover/upload:bg-orange-500/[0.02]">
                  <iconify-icon icon="solar:camera-bold-duotone" className="text-4xl text-orange-500 mb-3"></iconify-icon>
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 group-hover/upload:text-zinc-300">
                    {supportForm.screenshot ? supportForm.screenshot.name : t('uploadPrompt')}
                  </span>
                </div>
              </div>
            </div>

            <button 
              type="submit" 
              disabled={isSubmitting}
              className="w-full bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white font-black uppercase tracking-[0.3em] py-6 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-xl shadow-orange-950/20 active:scale-[0.98]"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <iconify-icon icon="solar:send-bold" className="text-lg"></iconify-icon>
                  {t('submitReport')}
                </>
              )}
            </button>
          </form>
        ) : (
          <form className="space-y-10" onSubmit={handleIdeaSubmit}>
            <div className="space-y-4">
              <div className="flex items-center gap-3 px-1">
                <div className="w-8 h-8 bg-orange-600/20 rounded-xl flex items-center justify-center">
                  <iconify-icon icon="solar:magic-stick-3-bold-duotone" className="text-orange-500 text-lg"></iconify-icon>
                </div>
                <label className="text-[10px] font-black text-orange-500 uppercase tracking-[0.2em]">{t('visionPrompt')}</label>
              </div>
              <textarea 
                rows="8"
                required
                value={ideaForm.content}
                onChange={(e) => setIdeaForm({...ideaForm, content: e.target.value})}
                className="w-full bg-black/50 border border-zinc-800 focus:border-orange-500/50 rounded-[32px] px-8 py-7 text-sm text-white outline-none resize-none leading-relaxed transition-all shadow-inner"
                placeholder={t('visionPlaceholder')}
              ></textarea>
            </div>
            <button 
              type="submit" 
              disabled={isSubmitting}
              className="w-full bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white font-black uppercase tracking-[0.3em] py-6 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-xl shadow-orange-950/20 active:scale-[0.98]"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <iconify-icon icon="solar:stars-bold" className="text-lg"></iconify-icon>
                  {t('submitIdea')}
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default SupportTab;

