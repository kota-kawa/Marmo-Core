import React from 'react';
import { useNavigate } from 'react-router-dom';
import logo from '../../assets/logo.png';

const InternalSidebar = ({ 
  t, 
  activeSection, 
  setActiveSection, 
  isSidebarOpen, 
  setIsSidebarOpen, 
  lang, 
  toggleLang, 
  handleLogout, 
  adminClients, 
  partnerApps,
  tickets = [],
  ideas = [] 
}) => {
  const navigate = useNavigate();
  return (
    <>
      {/* Mobile Toggle Overlay */}
      {isSidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden" onClick={() => setIsSidebarOpen(false)}></div>
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:relative inset-y-0 left-0 w-64 bg-zinc-900 text-white flex flex-col shrink-0 shadow-2xl z-40 border-r border-zinc-800 transition-transform duration-300 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="p-6 border-b border-zinc-800 flex items-center gap-3">
          <img src={logo} alt="Tokcer AI" className="h-8 w-auto" />
          <div className="text-xl font-black tracking-tighter uppercase text-white">
            <span className="text-blue-500">Core</span>
          </div>
        </div>

        {/* Language Toggle */}
        <div className="px-6 py-4 border-b border-zinc-800">
          <div className="flex bg-black rounded-lg p-1 border border-zinc-800">
            <button 
              onClick={() => toggleLang('id')}
              className={`flex-1 py-1 text-[10px] font-black rounded ${lang === 'id' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              ID
            </button>
            <button 
              onClick={() => toggleLang('en')}
              className={`flex-1 py-1 text-[10px] font-black rounded ${lang === 'en' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-600 hover:text-zinc-400'}`}
            >
              EN
            </button>
          </div>
        </div>
        
        <nav className="flex-1 mt-6 overflow-y-auto custom-scrollbar space-y-1">
          {[
            { id: 'overview', label: t('overview'), icon: 'solar:chart-square-bold-duotone' },
            { 
              id: 'approvals', 
              label: t('approvals'), 
              icon: 'solar:check-circle-bold-duotone', 
              badge: (adminClients.filter(c => !c.status || c.status.toLowerCase() === 'pending').length + partnerApps.length) || null 
            },
            { id: 'demo-approvals', label: 'Demo Approvals', icon: 'solar:user-check-bold-duotone' },
            { id: 'users', label: t('users'), icon: 'solar:users-group-rounded-bold-duotone' },
            { id: 'partners', label: t('partners'), icon: 'solar:users-group-two-rounded-bold-duotone' },
            { id: 'payouts', label: 'Pembayaran Partner', icon: 'solar:wallet-money-bold-duotone' },
            { id: 'tickets', label: t('tickets'), icon: 'solar:bug-bold-duotone', badge: tickets.length || null },
            { id: 'ideas', label: 'Saran Fitur', icon: 'solar:lightbulb-bold-duotone', badge: ideas.filter(i => i.status === 'draft' || i.status === 'open').length || null },
            { id: 'insight', label: t('businessInsight'), icon: 'solar:graph-bold-duotone' },
            { id: 'ai-gen', label: t('aiStrategy'), icon: 'solar:magic-stick-bold-duotone' },
            { id: 'tiktok-queue', label: 'TikTok Video Queue', icon: 'ri:tiktok-fill' },
            { id: 'token-audit', label: 'Token Audit & Billing', icon: 'solar:bill-list-bold-duotone' },
            { id: 'accounting', label: 'Accounting', icon: 'solar:calculator-bold-duotone' },
            { id: 'supabase', label: t('supabase'), icon: 'solar:database-bold-duotone' }
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => { setActiveSection(item.id); setIsSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 py-3.5 px-6 transition-all border-l-4 group ${activeSection === item.id ? 'bg-blue-600/10 border-blue-500 text-white shadow-[inset_0_0_20px_rgba(59,130,246,0.1)]' : 'border-transparent text-zinc-500 hover:bg-zinc-800/50 hover:text-white'}`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <iconify-icon icon={item.icon} className={`text-xl transition-transform group-hover:scale-110 ${activeSection === item.id ? 'text-blue-500' : 'text-zinc-500'}`}></iconify-icon>
                <span className="text-[10px] font-black uppercase tracking-[0.15em] truncate">{item.label}</span>
              </div>
              {item.badge && (
                <span className="bg-blue-600 text-[9px] font-black px-2 py-0.5 rounded-md text-white shadow-lg shadow-blue-600/30">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
        
        <div className="p-6 border-t border-zinc-800 bg-zinc-950/50">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xs shadow-lg">AD</div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-black uppercase tracking-widest text-white truncate">{t('superAdmin')}</p>
              <p className="text-[8px] font-bold text-zinc-500 truncate">admin@tokcer-ai.com</p>
            </div>
          </div>
          <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest text-center mb-4 italic">Core Command v2.4.1</p>
          
          <button onClick={handleLogout} className="w-full flex items-center justify-center gap-2 py-3 bg-red-500/10 text-red-500 border border-red-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all">
            <iconify-icon icon="solar:logout-3-bold-duotone" className="text-lg"></iconify-icon>
            {t('exitSystem')}
          </button>
        </div>
      </aside>
    </>
  );
};

export default InternalSidebar;
