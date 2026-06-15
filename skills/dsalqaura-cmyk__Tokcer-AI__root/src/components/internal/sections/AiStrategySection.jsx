import React from 'react';

const AiStrategySection = ({ 
  t, 
  aiConfig, 
  handleSaveAiConfig, 
  isLoading, 
  aiLogs,
  aiHistory = [],
  setAiConfig
}) => {
  const handleRestore = (key, value) => {
    if (window.confirm(`Restore this version of ${key}? Unsaved changes will be lost.`)) {
      setAiConfig(prev => ({ ...prev, [key]: value }));
    }
  };
  // Real calculation for display
  const stats = {
    totalClicks: aiLogs.length,
    totalInput: aiLogs.reduce((acc, curr) => acc + (Number(curr.input_tokens) || 0), 0),
    totalOutput: aiLogs.reduce((acc, curr) => acc + (Number(curr.output_tokens) || 0), 0),
    totalCost: aiLogs.reduce((acc, curr) => acc + (Number(curr.cost_usd) || 0), 0),
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
      {/* AI Usage & Billing Monitor */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          { label: 'Total AI Clicks', value: stats.totalClicks.toLocaleString(), icon: 'solar:mouse-circle-bold-duotone', color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { label: 'Total Tokens Used', value: (stats.totalInput + stats.totalOutput).toLocaleString(), icon: 'solar:CPU-bold-duotone', color: 'text-amber-500', bg: 'bg-amber-500/10' },
          { label: 'Estimated Cost', value: `$${stats.totalCost.toFixed(4)}`, icon: 'solar:wad-of-money-bold-duotone', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
          { label: 'Est. Remaining Balance', value: `$${(Number(aiConfig.ai_total_topup || 0) - stats.totalCost).toFixed(2)}`, icon: 'solar:wallet-bold-duotone', color: 'text-purple-500', bg: 'bg-purple-500/10', sub: `From $${Number(aiConfig.ai_total_topup || 0).toFixed(2)} Top-up` },
        ].map((s, i) => (
          <div key={i} className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 relative overflow-hidden group">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl ${s.bg} flex items-center justify-center border border-white/5`}>
                <iconify-icon icon={s.icon} className={`text-2xl ${s.color}`}></iconify-icon>
              </div>
              <div>
                <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">{s.label}</p>
                <p className={`text-xl font-black text-white tracking-tight`}>{s.value}</p>
                {s.sub && <p className="text-[8px] font-bold text-zinc-600 mt-1 uppercase tracking-widest">{s.sub}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-zinc-900/50 rounded-[2.5rem] border border-zinc-800 p-8 md:p-12 shadow-2xl relative overflow-hidden group">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 to-indigo-400"></div>
        <div className="flex justify-between items-center mb-10">
          <div>
            <h3 className="font-black text-2xl text-white uppercase tracking-tight">{t('aiManagement')}</h3>
            <p className="text-sm text-zinc-500 font-medium mt-1">Configure system behavior and retrieval knowledge</p>
          </div>
          <div className="w-14 h-14 bg-blue-600/10 rounded-2xl flex items-center justify-center border border-blue-500/20">
            <iconify-icon icon="solar:magic-stick-bold-duotone" className="text-3xl text-blue-500"></iconify-icon>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* System Prompt */}
          <div className="space-y-4">
            <div className="flex justify-between items-center px-2">
              <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">{t('strictInstructions')}</label>
              <iconify-icon icon="solar:shield-keyhole-bold-duotone" className="text-blue-500"></iconify-icon>
            </div>
            <textarea 
              className="w-full h-64 bg-black/40 border border-zinc-800 focus:border-blue-500/50 rounded-3xl p-6 text-sm text-zinc-300 outline-none resize-none leading-relaxed font-mono"
              value={aiConfig.system_prompt}
              onChange={(e) => setAiConfig({...aiConfig, system_prompt: e.target.value})}
            ></textarea>
          </div>

          {/* RAG Knowledge Base */}
          <div className="space-y-4">
            <div className="flex justify-between items-center px-2">
              <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">{t('knowledgeBase')}</label>
              <iconify-icon icon="solar:library-bold-duotone" className="text-amber-500"></iconify-icon>
            </div>
            <textarea 
              className="w-full h-64 bg-black/40 border border-zinc-800 focus:border-amber-500/50 rounded-3xl p-6 text-sm text-zinc-300 outline-none resize-none leading-relaxed font-mono"
              placeholder="Input knowledge chunks here for RAG..."
              value={aiConfig.rag_knowledge_base}
              onChange={(e) => setAiConfig({...aiConfig, rag_knowledge_base: e.target.value})}
            ></textarea>
          </div>
        </div>

        {/* AI Billing Config */}
        <div className="mt-8 pt-8 border-t border-zinc-800/50">
          <div className="flex items-center gap-3 mb-4 px-2">
            <iconify-icon icon="solar:wallet-bold-duotone" className="text-xl text-purple-500"></iconify-icon>
            <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">AI Credits Management</label>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* API Key hidden per Agreement - using master key from .env */}
            <div className="flex items-center justify-center bg-zinc-950/20 border border-zinc-800 rounded-2xl p-4">
              <span className="text-[10px] font-black text-zinc-600 uppercase tracking-widest">Master API Key Active & Secured</span>
            </div>
            <div>
              <label className="text-[9px] font-bold text-zinc-500 ml-4 mb-2 block uppercase">Total Top-up Amount (USD)</label>
              <input 
                type="number"
                step="0.01"
                className="w-full bg-black/40 border border-zinc-800 focus:border-purple-500/50 rounded-2xl px-6 py-4 text-sm text-zinc-300 outline-none font-mono"
                placeholder="e.g. 5.00"
                value={aiConfig.ai_total_topup || ''}
                onChange={(e) => setAiConfig({...aiConfig, ai_total_topup: e.target.value})}
              />
            </div>
          </div>
        </div>

        {/* Resend API Key Integration */}
        <div className="mt-8 pt-8 border-t border-zinc-800/50">
          <div className="flex items-center gap-3 mb-4 px-2">
            <iconify-icon icon="solar:letter-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
            <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Resend API Key Integration</label>
          </div>
          <div className="flex items-center justify-center bg-zinc-950/20 border border-zinc-800 rounded-2xl p-4">
            <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest flex items-center gap-2">
              <iconify-icon icon="solar:shield-check-bold" className="text-sm"></iconify-icon>
              Secured via Supabase Edge Secrets
            </span>
          </div>
        </div>

        {/* Marketplace API Integration */}
        <div className="mt-8 pt-8 border-t border-zinc-800/50 grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Shopee Config */}
          <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
              <iconify-icon icon="simple-icons:shopee" className="text-xl text-orange-500"></iconify-icon>
              <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Shopee API Config</label>
            </div>
            <input 
              type="text"
              className="w-full bg-black/40 border border-zinc-800 focus:border-orange-500/50 rounded-2xl px-6 py-4 text-sm text-zinc-300 outline-none font-mono"
              placeholder="Partner ID (e.g. 1234567)"
              value={aiConfig.shopee_partner_id || ''}
              onChange={(e) => setAiConfig({...aiConfig, shopee_partner_id: e.target.value})}
            />
            <input 
              type="password"
              className="w-full bg-black/40 border border-zinc-800 focus:border-orange-500/50 rounded-2xl px-6 py-4 text-sm text-zinc-300 outline-none font-mono"
              placeholder="Partner Key"
              value={aiConfig.shopee_partner_key || ''}
              onChange={(e) => setAiConfig({...aiConfig, shopee_partner_key: e.target.value})}
            />
          </div>

          {/* TikTok Config */}
          <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
              <iconify-icon icon="ri:tiktok-fill" className="text-xl text-white"></iconify-icon>
              <label className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">TikTok Shop API Config</label>
            </div>
            <input 
              type="text"
              className="w-full bg-black/40 border border-zinc-800 focus:border-white/50 rounded-2xl px-6 py-4 text-sm text-zinc-300 outline-none font-mono"
              placeholder="App ID / Service ID"
              value={aiConfig.tiktok_app_id || ''}
              onChange={(e) => setAiConfig({...aiConfig, tiktok_app_id: e.target.value})}
            />
            <input 
              type="password"
              className="w-full bg-black/40 border border-zinc-800 focus:border-white/50 rounded-2xl px-6 py-4 text-sm text-zinc-300 outline-none font-mono"
              placeholder="App Secret"
              value={aiConfig.tiktok_app_secret || ''}
              onChange={(e) => setAiConfig({...aiConfig, tiktok_app_secret: e.target.value})}
            />
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button 
            onClick={handleSaveAiConfig}
            disabled={isLoading}
            className="px-10 py-4 bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-black uppercase tracking-[0.3em] rounded-2xl shadow-xl shadow-blue-600/20 transition-all active:scale-95 disabled:opacity-50"
          >
            {isLoading ? 'SAVING...' : t('saveConfig')}
          </button>
        </div>
      </div>

      {/* AI Config History */}
      <div className="bg-zinc-900/50 rounded-[2.5rem] border border-zinc-800 overflow-hidden shadow-2xl mt-8">
        <div className="p-8 border-b border-zinc-800 bg-zinc-950/50 flex justify-between items-center">
          <h3 className="font-black text-white uppercase tracking-tight">Config Version History</h3>
          <iconify-icon icon="solar:history-bold-duotone" className="text-xl text-zinc-500"></iconify-icon>
        </div>
        <div className="p-8">
          <div className="space-y-4">
            {aiHistory.length > 0 ? aiHistory.map((h, i) => (
              <div key={i} className="flex items-center justify-between p-4 bg-zinc-950/50 rounded-2xl border border-zinc-800 hover:border-zinc-700 transition-all">
                <div className="flex items-center gap-4">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${h.key === 'system_prompt' ? 'bg-blue-600/10 text-blue-500' : 'bg-amber-600/10 text-amber-500'}`}>
                    <iconify-icon icon={h.key === 'system_prompt' ? 'solar:shield-keyhole-bold' : 'solar:library-bold'}></iconify-icon>
                  </div>
                  <div>
                    <div className="text-[10px] font-black text-white uppercase tracking-widest">{h.key.replace('_', ' ')}</div>
                    <div className="text-[9px] text-zinc-500 font-medium">Changed on {new Date(h.created_at).toLocaleString()}</div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => {
                      const win = window.open('', '_blank');
                      win.document.write(`<pre style="background:#111;color:#eee;padding:20px;font-family:mono;white-space:pre-wrap">${h.old_value}</pre>`);
                    }}
                    className="text-[9px] font-black text-zinc-500 hover:text-white uppercase tracking-widest px-3 py-1.5 rounded-lg border border-zinc-800 hover:bg-zinc-800"
                  >
                    View Diff
                  </button>
                  <button 
                    onClick={() => handleRestore(h.key, h.old_value)}
                    className="text-[9px] font-black text-emerald-500 hover:text-emerald-400 uppercase tracking-widest px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10"
                  >
                    Restore
                  </button>
                </div>
              </div>
            )) : (
              <div className="p-8 text-center text-zinc-500 text-[10px] font-black uppercase tracking-widest italic">No version history yet</div>
            )}
          </div>
        </div>
      </div>

      {/* AI Logs */}
      <div className="bg-zinc-900/50 rounded-[2.5rem] border border-zinc-800 overflow-hidden shadow-2xl mt-8">
        <div className="p-8 border-b border-zinc-800 bg-zinc-950/50">
          <h3 className="font-black text-white uppercase tracking-tight">{t('aiLogs')}</h3>
        </div>
        <div className="p-8">
          <table className="w-full text-left border-separate border-spacing-y-2">
            <thead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">
              <tr>
                <th className="px-4 pb-2">{t('user')}</th>
                <th className="px-4 pb-2">{t('task')}</th>
                <th className="px-4 pb-2 text-center">Tokens (In/Out)</th>
                <th className="px-4 pb-2 text-center">Cost (USD)</th>
                <th className="px-4 pb-2 text-right">{t('time')}</th>
              </tr>
            </thead>
            <tbody>
              {aiLogs.length > 0 ? aiLogs.map((log, i) => (
                <tr key={i} className="bg-zinc-950/50 hover:bg-zinc-800/50 transition-all group">
                  <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800">
                    <div className="font-black text-white text-xs uppercase tracking-tight">{log.profiles?.full_name || 'System User'}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800">
                     <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{log.feature || 'UNKNOWN TASK'}</span>
                     <div className="text-[9px] text-zinc-500 mt-1 line-clamp-1 max-w-xs" title={log.prompt}>{log.prompt || '-'}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                     <div className="text-[10px] font-black text-blue-400">{log.input_tokens || 0} / {log.output_tokens || 0}</div>
                     <div className="text-[8px] font-bold text-zinc-600 uppercase">Tokens</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                     <span className="bg-emerald-600/10 text-emerald-400 text-[10px] font-black px-3 py-1 rounded-lg">${Number(log.cost_usd || 0).toFixed(5)}</span>
                  </td>
                  <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800 text-right">
                     <span className="text-[10px] font-bold text-zinc-600 uppercase italic">{new Date(log.created_at).toLocaleTimeString()}</span>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" className="p-8 text-center text-zinc-500 text-[10px] font-black uppercase tracking-widest italic">No AI activity recorded yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AiStrategySection;
