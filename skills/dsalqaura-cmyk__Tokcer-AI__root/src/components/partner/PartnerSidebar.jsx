import React from 'react';
import logo from '../../assets/logo.png';

const PartnerSidebar = ({ 
  t, 
  activeTab, 
  setActiveTab, 
  isMobileMenuOpen, 
  setIsMobileMenuOpen, 
  lang, 
  toggleLang, 
  handleLogout 
}) => {
  const tabs = ['onboard', 'subscribers', 'leaderboard', 'payment', 'support', 'academy', 'profile', 'commissionScheme'];

  return (
    <>
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/80 backdrop-blur-sm z-[100]" onClick={() => setIsMobileMenuOpen(false)}>
          <aside className="w-80 h-full bg-zinc-950 border-r border-zinc-800 flex flex-col animate-in slide-in-from-left duration-300">
            <div className="p-8 border-b border-zinc-800 flex items-center justify-between">
              <img src={logo} alt="Tokcer AI" className="h-8 w-auto" />
              <button onClick={() => setIsMobileMenuOpen(false)} className="text-zinc-500 hover:text-white transition-colors">
                <iconify-icon icon="solar:close-circle-bold" className="text-2xl"></iconify-icon>
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-2">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => { setActiveTab(tab); setIsMobileMenuOpen(false); }}
                  className={`w-full flex items-center gap-4 px-6 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                    activeTab === tab 
                      ? "bg-orange-600/10 text-orange-500 border border-orange-600/20" 
                      : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300 border border-transparent"
                  }`}
                >
                  <iconify-icon icon={
                    tab === 'onboard' ? 'solar:user-plus-bold-duotone' :
                    tab === 'subscribers' ? 'solar:users-group-rounded-bold-duotone' : 
                    tab === 'leaderboard' ? 'solar:ranking-bold-duotone' : 
                    tab === 'payment' ? 'solar:card-transfer-bold-duotone' :
                    tab === 'support' ? 'solar:chat-round-dots-bold-duotone' :
                    tab === 'profile' ? 'solar:user-id-bold-duotone' :
                    tab === 'commissionScheme' ? 'solar:money-bag-bold-duotone' :
                    'solar:notebook-bold-duotone'
                  } className={`text-xl ${activeTab === tab ? 'text-orange-500' : 'text-zinc-500'}`}></iconify-icon>
                  {t(tab)}
                </button>
              ))}
            </div>

            <div className="p-6 border-t border-zinc-800 bg-black/40 flex flex-col gap-4 shrink-0">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Language</span>
                <div className="flex bg-zinc-900 rounded-xl p-1 border border-zinc-800">
                  <button 
                    onClick={() => { toggleLang('id'); setIsMobileMenuOpen(false); }}
                    className={`px-4 py-1.5 text-[10px] font-bold rounded-lg transition-all ${lang === 'id' ? 'bg-orange-600 text-white shadow-lg' : 'text-zinc-500 hover:text-white'}`}
                  >
                    ID
                  </button>
                  <button 
                    onClick={() => { toggleLang('en'); setIsMobileMenuOpen(false); }}
                    className={`px-4 py-1.5 text-[10px] font-bold rounded-lg transition-all ${lang === 'en' ? 'bg-orange-600 text-white shadow-lg' : 'text-zinc-500 hover:text-white'}`}
                  >
                    EN
                  </button>
                </div>
              </div>
              <button 
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-black text-rose-500 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all uppercase tracking-[0.2em]"
              >
                <iconify-icon icon="solar:logout-2-linear" className="text-lg"></iconify-icon>
                {t('logout')}
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};

export default PartnerSidebar;
