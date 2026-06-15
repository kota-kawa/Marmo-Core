import React from 'react';

const InternalHeader = ({ 
  t, 
  activeSection, 
  setIsSidebarOpen 
}) => {
  return (
    <header className="bg-zinc-900/50 backdrop-blur-xl border-b border-zinc-800 py-4 px-8 flex justify-between items-center sticky top-0 z-10 shrink-0">
      <div className="flex items-center gap-4">
         {/* Mobile Menu Trigger */}
         <button onClick={() => setIsSidebarOpen(true)} className="lg:hidden w-10 h-10 flex items-center justify-center bg-zinc-800 rounded-xl border border-zinc-700">
           <iconify-icon icon="solar:hamburger-menu-bold" className="text-white text-xl"></iconify-icon>
         </button>
         <h1 className="text-xl font-black text-white uppercase tracking-tight">
           {activeSection === 'partners' ? 'Partnership' : activeSection.toUpperCase()} <span className="text-zinc-500 font-light">| Command Center</span>
         </h1>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1 text-right">{t('systemStatus')}</p>
          <p className="text-sm font-bold text-green-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            {t('liveSynced')}
          </p>
        </div>
      </div>
    </header>
  );
};

export default InternalHeader;
