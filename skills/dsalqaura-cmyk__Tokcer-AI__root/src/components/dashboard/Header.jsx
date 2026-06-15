import React from 'react';
import logo from '../../assets/logo.png';

const Header = ({ setIsSidebarOpen }) => {
  return (
    <div className="lg:hidden fixed top-0 left-0 right-0 z-[60] flex items-center justify-between p-4 bg-zinc-950 border-b border-zinc-800 shadow-xl">
      <div className="flex items-center gap-3">
        <img src={logo} alt="Tokcer AI" className="h-7 w-auto" />
      </div>
      <button 
        onClick={() => setIsSidebarOpen(true)} 
        className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-300 hover:text-white transition-all active:scale-95"
        aria-label="Open Sidebar"
      >
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Menu</span>
        <iconify-icon icon="solar:hamburger-menu-bold-duotone" className="text-xl text-orange-500"></iconify-icon>
      </button>
    </div>
  );
};

export default Header;
