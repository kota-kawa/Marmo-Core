import React from 'react';

const DashboardOnboarding = ({ onConnect }) => {
  return (
    <div className="mb-8 animate-in slide-in-from-top-4 duration-700">
      <div className="bg-gradient-to-r from-orange-600 to-amber-500 rounded-3xl p-6 md:p-8 shadow-xl shadow-orange-600/20 relative overflow-hidden group">
        {/* Decorative Elements */}
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform duration-700">
          <iconify-icon icon="solar:shop-2-bold" className="text-9xl text-white"></iconify-icon>
        </div>
        <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        
        <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-center md:text-left">
            <h3 className="text-xl md:text-2xl font-black text-white mb-2 uppercase tracking-tight">🚀 Selamat Datang di Tokcer AI!</h3>
            <p className="text-sm text-orange-50 text-balance max-w-xl">
              Dashboard kamu saat ini masih menggunakan <strong>Data Contoh (Sample Mode)</strong>. 
              Hubungkan toko Shopee atau TikTok kamu sekarang untuk melihat analisis data real-time dan cuan maksimal!
            </p>
          </div>
          <button 
            onClick={onConnect}
            className="whitespace-nowrap bg-white text-orange-600 px-8 py-4 rounded-2xl font-black text-xs uppercase tracking-[0.2em] shadow-xl hover:bg-orange-50 hover:scale-105 active:scale-95 transition-all flex items-center gap-3"
          >
            <iconify-icon icon="solar:link-bold" className="text-lg"></iconify-icon>
            Hubungkan Toko Sekarang
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardOnboarding;
