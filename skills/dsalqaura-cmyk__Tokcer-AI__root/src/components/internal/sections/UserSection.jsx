import React from 'react';

const UserSection = ({ 
  t, 
  adminClients = [], 
  getTierBadgeClass, 
  setShowUserStats 
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-zinc-900/50 rounded-3xl border border-zinc-800 overflow-hidden">
        <div className="p-6 border-b border-zinc-800 bg-zinc-950/50 flex justify-between items-center">
           <h3 className="font-black text-white uppercase tracking-tight">{t('userBaseMonitor')}</h3>
        </div>
        <div className="p-8">
          <table className="w-full text-left border-separate border-spacing-y-2">
            <thead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">
              <tr>
                <th className="px-4 pb-2">{t('subscriberInfo')}</th>
                <th className="px-4 pb-2">{t('activePlan')}</th>
                <th className="px-4 pb-2 text-center">AI CREDITS</th>
                <th className="px-4 pb-2 text-center">EXPIRES AT</th>
                <th className="px-4 pb-2">{t('health')}</th>
                <th className="px-4 pb-2 text-right">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {adminClients.length > 0 ? adminClients.map((u) => (
                <tr key={u.id} className="bg-zinc-950/50 hover:bg-zinc-800/50 transition-all group">
                  <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800">
                    <div className="font-black text-white text-sm tracking-tight">{u.shop_name}</div>
                    <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest opacity-60">ID: {u.id?.substring(0,8)} • {u.email}</div>
                    {/* WhatsApp untuk quick follow-up */}
                    {u.whatsapp && (
                      <div className="flex items-center gap-1.5 mt-1">
                        <iconify-icon icon="solar:phone-bold-duotone" className="text-xs text-emerald-500"></iconify-icon>
                        <a
                          href={`https://wa.me/${u.whatsapp.replace(/\D/g,'').replace(/^0/,'62')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[9px] font-bold text-emerald-500 hover:text-emerald-400 transition-colors"
                        >
                          {u.whatsapp}
                        </a>
                      </div>
                    )}
                  </td>
                  <td className="p-4 border-y border-zinc-800">
                     <span className={`${getTierBadgeClass(u.tier)} text-[9px] font-black px-3 py-1 rounded-lg uppercase`}>{u.tier || u.plan}</span>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                     <div className={`text-[10px] font-black ${
                       (() => {
                         const v = u.profiles?.ai_tokens ?? u.profiles?.tokens;
                         if (v === undefined || v === null) return 'text-zinc-600';
                         if (Number(v) <= 10) return 'text-red-400';
                         if (Number(v) <= 50) return 'text-amber-400';
                         return 'text-blue-400';
                       })()
                     }`}>
                       {(() => {
                         const v = u.profiles?.ai_tokens ?? u.profiles?.tokens;
                         return (v !== undefined && v !== null) ? Number(v).toLocaleString('id-ID') : '-';
                       })()}
                     </div>
                  </td>
                  <td className="p-4 border-y border-zinc-800 text-center">
                     <div className="text-[10px] font-bold text-zinc-400">
                       {u.expires_at ? new Date(u.expires_at).toLocaleDateString('id-ID', {day: 'numeric', month: 'short', year: 'numeric'}) : '-'}
                     </div>
                  </td>
                  <td className="p-4 border-y border-zinc-800">
                     {(() => {
                        const isExpired = u.status === 'expired' || (u.status === 'active' && u.expires_at && new Date(u.expires_at) < new Date());
                        const isNearExpiry = u.status === 'active' && u.expires_at && new Date(u.expires_at).getTime() - new Date().getTime() < 3 * 24 * 60 * 60 * 1000;
                        
                        let statusText = u.status?.toUpperCase() || 'UNKNOWN';
                        let statusColor = (u.status === 'active' || u.status === 'paid') ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20' : 'text-amber-500 bg-amber-500/10 border-amber-500/20';

                        if (isExpired) {
                            statusText = 'EXPIRED';
                            statusColor = 'text-rose-500 bg-rose-500/10 border-rose-500/20';
                        } else if (isNearExpiry) {
                            statusText = 'NEAR EXPIRY (H-3)';
                            statusColor = 'text-orange-500 bg-orange-500/10 border-orange-500/20 animate-pulse';
                        }

                        return <span className={`text-[10px] font-black px-2 py-1 rounded-md border ${statusColor}`}>{statusText}</span>;
                     })()}
                  </td>
                  <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800 text-right">
                     <button onClick={() => setShowUserStats(u)} className="px-4 py-2 bg-blue-600/10 text-blue-400 text-[9px] font-black uppercase tracking-widest rounded-xl border border-blue-500/20 hover:bg-blue-600 hover:text-white transition-all">{t('viewDetails')}</button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="6" className="py-20 text-center text-zinc-600 italic text-sm">No users found in database.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default UserSection;
