import React from 'react';
import { useNavigate } from 'react-router-dom';
import logo from '../../assets/logo.png';

const Sidebar = ({ 
  t, 
  activeMenu, 
  setActiveMenu, 
  isSidebarOpen,
  setIsSidebarOpen, 
  lang, 
  setLang, 
  profile, 
  user,
  handleLogout,
  clientData
}) => {
  const navigate = useNavigate();
  const plan = (profile?.subscription_plan || 'starter').toLowerCase();

  const isLocked = (tab) => {
    // Admin bypass
    if (plan === 'ultimate' || user?.email === 'admin@tokcer-ai.com' || localStorage.getItem('tokcer_admin_auth') === 'true') return false;
    
    // Demo Plan Restriction
    if (plan === 'demo') {
      const allowedDemoTabs = ['tab-ai', 'tab-market', 'tab-support', 'tab-billing', 'tab-account'];
      if (!allowedDemoTabs.includes(tab)) return true;
      return false;
    }

    const permissions = {
      'tab-health': ['pro', 'elite', 'ultimate'],
      'tab-market': ['elite', 'ultimate'],
    };

    if (permissions[tab] && !permissions[tab].includes(plan)) return true;
    return false;
  };

  const renderMenuItem = (tab, icon, label, isAi = false) => {
    const locked = isLocked(tab);
    const active = activeMenu === tab;

    return (
      <button 
        onClick={() => { 
          // Semua menu bisa diklik — konten yang akan menampilkan blur overlay
          setActiveMenu(tab); 
          setIsSidebarOpen(false); 
        }} 
        className={`w-full flex items-center justify-between px-3 py-2 md:py-2.5 rounded-xl text-sm transition-all shrink-0 group relative ${
          active 
            ? 'font-medium bg-orange-950/50 text-orange-500 border border-orange-900/50 border-l-2' 
            : locked
              ? 'font-normal text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 border border-transparent'
              : 'font-normal text-zinc-400 hover:text-white hover:bg-zinc-800 border border-transparent'
        }`}
      >
        <div className="flex items-center gap-3 relative z-10">
          <iconify-icon icon={icon} className={`text-lg ${isAi && !active && !locked ? 'text-orange-500' : ''}`}></iconify-icon>
          <span>{label}</span>
        </div>
        
        {locked && (
          <iconify-icon icon="solar:lock-password-bold" className="text-zinc-600 text-sm relative z-10"></iconify-icon>
        )}
        
        {isAi && !active && !locked && (
          <div className="absolute inset-0 bg-orange-950/50 opacity-0 group-hover:opacity-100 rounded-xl transition-opacity"></div>
        )}
      </button>
    );
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden" 
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:relative inset-y-0 left-0 w-64 border-r border-zinc-800 bg-black flex flex-col shrink-0 z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${isSidebarOpen ? '!translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <img src={logo} alt="Tokcer AI" className="h-8 w-auto" />
          </h1>
          <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden text-zinc-400 hover:text-white">
            <iconify-icon icon="solar:close-circle-linear" className="text-2xl"></iconify-icon>
          </button>
        </div>
        
        <div className="p-4 w-full overflow-y-auto custom-scrollbar flex-1">
          <div className="text-xs font-medium text-zinc-500 uppercase tracking-[0.2em] mb-4 px-3">
            {t('overview')}
          </div>
          <nav className="flex flex-col gap-1.5 md:gap-2">
            {renderMenuItem('tab-dash', 'solar:widget-linear', t('dashboard'))}
            {renderMenuItem('tab-omzet', 'solar:chart-square-linear', t('revenue'))}
            {renderMenuItem('tab-inventory', 'solar:box-linear', t('inventory'))}
            {renderMenuItem('tab-analytics', 'solar:graph-up-linear', t('analytics'))}
            {renderMenuItem('tab-ai', 'solar:magic-stick-3-linear', t('aiGenerator'), true)}
            {renderMenuItem('tab-support', 'solar:headphones-round-linear', t('supportCenter'))}
            {renderMenuItem('tab-health', 'solar:shield-check-linear', t('healthScore'))}
            {renderMenuItem('tab-market', 'solar:global-linear', t('marketIntel'))}
            {renderMenuItem('tab-account', 'solar:shield-keyhole-linear', t('accountSecurity'))}
            {renderMenuItem('tab-billing', 'solar:card-2-linear', 'Billing & Langganan')}
            {renderMenuItem('tab-connections', 'solar:link-linear', 'Marketplace Sync')}
            
            {/* HPP Calculator - Redirects to separate page */}
            <button 
              onClick={() => navigate('/hpp-calculator')} 
              className="w-full flex items-center justify-between px-3 py-2 md:py-2.5 rounded-xl text-sm transition-all shrink-0 group font-normal text-zinc-400 hover:text-white hover:bg-zinc-800 border border-transparent"
            >
              <div className="flex items-center gap-3 relative z-10">
                <iconify-icon icon="solar:calculator-minimalistic-linear" className="text-lg text-emerald-500"></iconify-icon>
                <span>HPP & Margin Calc</span>
              </div>
              <iconify-icon icon="solar:arrow-right-linear" className="text-zinc-600 text-[10px]"></iconify-icon>
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-zinc-800">
          {/* Language Toggle - HIDDEN per Agreement (Point 5) */}

          {/* User Tier Card */}
          <div className="mb-4 px-2">
            {(() => {
              const plan = (profile?.subscription_plan || 'starter').toLowerCase();
              const isUltimate = plan === 'ultimate';
              
              const planConfigs = {
                demo: { color: 'from-indigo-950/60 to-purple-950/40', border: 'border-indigo-700/40', text: 'text-indigo-400', icon: 'solar:user-check-bold', bgIcon: 'bg-indigo-500', glow: 'bg-indigo-500/10' },
                starter: { color: 'from-zinc-950/60 to-zinc-900/40', border: 'border-zinc-700/40', text: 'text-zinc-400', icon: 'solar:box-linear', bgIcon: 'bg-zinc-500', glow: 'bg-zinc-500/10' },
                pro: { color: 'from-blue-950/60 to-indigo-950/40', border: 'border-blue-700/40', text: 'text-blue-400', icon: 'solar:medal-star-bold', bgIcon: 'bg-blue-500', glow: 'bg-blue-500/10' },
                elite: { color: 'from-indigo-950/60 to-purple-950/40', border: 'border-indigo-700/40', text: 'text-indigo-400', icon: 'solar:crown-bold', bgIcon: 'bg-indigo-500', glow: 'bg-indigo-500/10' },
                ultimate: { color: 'from-amber-950/60 to-orange-950/40', border: 'border-amber-700/40', text: 'text-amber-400', icon: 'solar:crown-bold', bgIcon: 'bg-gradient-to-br from-amber-400 to-orange-500', glow: 'bg-amber-500/10' }
              };
              
              const conf = planConfigs[plan] || planConfigs.starter;

              // Max quota per plan (SYNCED with System Specifications)
              const planMaxQuota = { demo: 30, starter: 50, pro: 300, elite: 1000, ultimate: Infinity };
              const maxQuota = planMaxQuota[plan] ?? 50;

              const formatDate = (dateStr) => {
                if (!dateStr) return 'Selamanya';
                try {
                  const date = new Date(dateStr);
                  if (isNaN(date.getTime())) return 'Selamanya';
                  const months = [
                    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
                  ];
                  return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
                } catch (e) {
                  return 'Selamanya';
                }
              };
              
              return (
                <div className={`bg-gradient-to-br ${conf.color} border ${conf.border} rounded-xl p-3 relative overflow-hidden`}>
                  <div className={`absolute -top-4 -right-4 w-12 h-12 ${conf.glow} rounded-full blur-xl pointer-events-none`}></div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-6 h-6 rounded-md ${conf.bgIcon} flex items-center justify-center shadow-sm`}>
                        <iconify-icon icon={conf.icon} className="text-white text-[10px]"></iconify-icon>
                      </div>
                      <div>
                        <p className={`text-[8px] ${conf.text}/80 uppercase tracking-widest font-semibold`}>{t('planActive')}</p>
                        <p className={`text-xs font-bold ${isUltimate ? 'text-amber-300' : 'text-white'} leading-none capitalize`}>
                          {plan}
                        </p>
                      </div>
                    </div>
                    <span className={`text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${isUltimate ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-zinc-800 text-zinc-400 border border-zinc-700'}`}>
                      ✓ {t('active')}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between items-center text-[9px]">
                      <span className="text-zinc-500">{t('aiQuota')}</span>
                      {isUltimate ? (
                        <span className="text-amber-400 font-bold flex items-center gap-1">
                          <iconify-icon icon="solar:star-bold" className="text-[10px]"></iconify-icon>
                          Unlimited
                        </span>
                      ) : (
                        <span className="text-zinc-400 font-semibold">{profile?.tokens || 0} / {maxQuota}</span>
                      )}
                    </div>
                    <div className="w-full bg-zinc-800/80 rounded-full h-1">
                      <div className={`h-1 rounded-full ${isUltimate ? 'bg-gradient-to-r from-amber-400 to-orange-500' : 'bg-orange-500'}`} style={{width: `${isUltimate ? 100 : Math.min(100, ((profile?.tokens || 0) / maxQuota) * 100)}%`}}></div>
                    </div>
                  </div>
                  <p className="text-[8px] text-zinc-600 mt-1.5 text-center italic">
                    {t('validUntil')} {formatDate(clientData?.expires_at || clientData?.expired_at || profile?.expired_at || profile?.expires_at)}
                  </p>
                </div>
              );
            })()}
          </div>

          <div className="mb-4 px-2">
            <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider mb-1">{t('loggedAs')}</p>
            <p className="text-sm text-zinc-300 truncate">{user?.email || 'admin@tokoanda.com'}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors border border-transparent hover:border-rose-500/50"
          >
            <iconify-icon icon="solar:logout-2-linear" className="text-xl"></iconify-icon>
            {t('logout')}
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
