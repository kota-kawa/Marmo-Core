import React from 'react';

const ApprovalSection = ({ 
  t, 
  activeAppTab, 
  setActiveAppTab, 
  adminClients, 
  partnerApps, 
  MOCK_USERS, 
  getTierBadgeClass, 
  setSelectedPartnerApp, 
  handleOpenApproveModal,
  setShowApproveModal, 
  handleApprove,
  handleReject,
  handleRemindPartner,
  setShowModal,
  setSelectedClient
}) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-zinc-900/50 rounded-3xl border border-zinc-800 overflow-hidden">
        <div className="flex space-x-8 px-8 border-b border-zinc-800 bg-zinc-950/50 pt-6">
          {[
            { id: 'app-subs', label: t('paymentsUpgrades') },
            { id: 'new-user', label: t('identityVerification') },
            { id: 'new-partner', label: t('partnerApplications') }
          ].map((tab) => (
            <button 
              key={tab.id}
              onClick={() => setActiveAppTab(tab.id)} 
              className={`pb-5 text-[11px] font-black uppercase tracking-widest relative transition-colors ${activeAppTab === tab.id ? 'text-blue-500' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              {tab.label}
              {activeAppTab === tab.id && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 shadow-[0_-2px_10px_rgba(59,130,246,0.5)]"></div>}
            </button>
          ))}
        </div>

        <div className="p-8">
          <table className="w-full text-left border-separate border-spacing-y-2">
            <thead className="text-zinc-500 text-[10px] font-black uppercase tracking-widest">
              <tr>
                <th className="px-4 pb-2">{t('identification')}</th>
                <th className="px-4 pb-2">Kontak</th>
                <th className="px-4 pb-2">{activeAppTab === 'new-partner' ? t('tier') : t('statusPlan')}</th>
                <th className="px-4 pb-2 text-center">{t('picPartner')}</th>
                <th className="px-4 pb-2 text-center">Bukti</th>
                <th className="px-4 pb-2 text-center">{t('refSource')}</th>
                <th className="px-4 pb-2 text-right">{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {(activeAppTab === 'app-subs' 
                ? adminClients.filter(c => c.status?.toLowerCase() === 'pending') 
                : activeAppTab === 'new-partner' ? partnerApps 
                : adminClients.filter(c => c.status?.toLowerCase() === 'warning')
              ).map((item, i) => (
                <tr key={i} className="bg-zinc-900/30 hover:bg-zinc-800/50 transition-all group">
                  <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800/50">
                    <div className="font-black text-white text-sm tracking-tight group-hover:text-blue-400 transition-colors">
                      {item.nama || item.name || item.shop_name}
                    </div>
                    <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest opacity-60">ID: {item.id?.substring(0,6)}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800/50">
                    <div className="text-[10px] font-bold text-white tracking-tight">{item.email}</div>
                    <div className="text-[9px] text-emerald-500 font-black mt-0.5">{item.whatsapp || '-'}</div>
                  </td>
                  <td className="p-4 border-y border-zinc-800/50">
                    <div className="flex flex-col items-start gap-1">
                      <span className={`${getTierBadgeClass(activeAppTab === 'new-partner' ? 'bronze' : (item.plan || item.tier || 'starter'))} text-[9px] font-black px-3 py-1 rounded-lg uppercase border border-white/5`}>
                        {activeAppTab === 'new-partner' ? 'Bronze' : (item.plan || item.tier || 'Starter')}
                      </span>
                      {item.billing_cycle && (
                        <span className="text-[8px] font-bold text-zinc-500 uppercase tracking-widest pl-1">{item.billing_cycle}</span>
                      )}
                      {activeAppTab === 'app-subs' && (
                        <span className={`mt-1 px-2 py-0.5 border text-[8px] font-black uppercase rounded-md tracking-widest flex items-center gap-1 w-fit ${
                          item.is_renewal ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                        }`}>
                          <iconify-icon icon={item.is_renewal ? "solar:refresh-bold-duotone" : "solar:star-fall-bold-duotone"}></iconify-icon>
                          {item.is_renewal ? 'RENEWAL' : 'NEW'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-4 border-y border-zinc-800/50 text-center">
                    <div className="flex flex-col items-center">
                        <span className="text-[10px] font-bold text-zinc-400">{item.pic || item.partners?.full_name || 'Direct Access'}</span>
                        {item.partners?.email && (
                            <button 
                                onClick={() => handleRemindPartner(item)}
                                className="mt-1 px-2 py-0.5 bg-amber-500/10 text-amber-500 text-[8px] font-black uppercase rounded border border-amber-500/20 hover:bg-amber-500 hover:text-white transition-all"
                            >
                                <iconify-icon icon="solar:bell-bing-bold" className="mr-1"></iconify-icon>
                                Remind
                            </button>
                        )}
                    </div>
                  </td>
                  <td className="p-4 border-y border-zinc-800/50 text-center">
                    {item.payment_proof_url ? (
                      <a href={item.payment_proof_url} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:underline flex flex-col items-center gap-1 text-[8px] font-black uppercase">
                        <iconify-icon icon="solar:camera-bold" className="text-sm"></iconify-icon>
                        Lihat
                      </a>
                    ) : (
                      <span className="text-zinc-700">-</span>
                    )}
                  </td>
                  <td className="p-4 border-y border-zinc-800/50 text-center">
                    <span className="text-[10px] font-black text-blue-500 tracking-tighter uppercase bg-blue-500/5 px-2 py-1 rounded border border-blue-500/10">{item.ref || item.payment_method || 'SYSTEM'}</span>
                  </td>
                  <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800/50 text-right">
                    <div className="flex items-center justify-end gap-3">
                      {item.status === 'pending' || item.status === 'warning' || !item.status || item.status === 'agreed' ? (
                        <>
                          {activeAppTab === 'new-partner' ? (
                            <>
                              <button 
                                onClick={() => setSelectedPartnerApp(item)} 
                                className="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-white hover:text-black rounded-xl border border-zinc-700 transition-all shadow-lg"
                                title="Lihat Detail Strategi"
                              >
                                <iconify-icon icon="solar:eye-bold-duotone" className="text-xl"></iconify-icon>
                              </button>
                              <button 
                                onClick={() => handleOpenApproveModal(item)} 
                                className="px-6 py-2 bg-amber-600 hover:bg-amber-500 text-white text-[9px] font-black uppercase tracking-[0.2em] rounded-xl transition-all shadow-lg shadow-amber-600/20 active:scale-95"
                              >
                                Approve & Setup
                              </button>
                            </>
                          ) : (
                            <>
                              <button 
                                onClick={() => { setSelectedClient(item); setShowModal(true); }} 
                                className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white text-[9px] font-black uppercase tracking-[0.2em] rounded-xl transition-all shadow-lg shadow-blue-600/20 active:scale-95"
                              >
                                Approve
                              </button>
                              <button onClick={() => handleReject(item)} className="px-6 py-2 bg-zinc-800 hover:bg-rose-600 text-zinc-500 hover:text-white text-[9px] font-black uppercase tracking-[0.2em] rounded-xl border border-zinc-700 transition-all active:scale-95">Reject</button>
                            </>
                          )}
                        </>
                      ) : (
                        <span className="text-emerald-500 text-[10px] font-black uppercase px-4 flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                          {item.status}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ApprovalSection;
