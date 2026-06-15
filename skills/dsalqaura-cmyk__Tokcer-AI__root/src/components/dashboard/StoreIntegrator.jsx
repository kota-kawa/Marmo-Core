import React from 'react';

const StoreIntegrator = ({ t, onBack }) => {
  const platforms = [
    { 
      id: 'shopee', 
      name: 'Shopee', 
      icon: 'simple-icons:shopee', 
      color: 'bg-[#EE4D2D]', 
      desc: 'Integrasi resmi Shopee Open Platform. Sinkronisasi pesanan, stok, dan chat otomatis.',
      status: 'Ready'
    },
    { 
      id: 'tiktok', 
      name: 'TikTok Shop', 
      icon: 'ri:tiktok-fill', 
      color: 'bg-black', 
      desc: 'Kelola keranjang kuning dan live streaming data langsung dari Dashboard Tokcer AI.',
      status: 'Ready'
    }
  ];

  return (
    <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
      <button 
        onClick={onBack}
        className="mb-6 flex items-center gap-2 text-zinc-500 hover:text-white transition-colors group"
      >
        <iconify-icon icon="solar:alt-arrow-left-linear" className="group-hover:-translate-x-1 transition-transform"></iconify-icon>
        <span className="text-sm font-medium">Kembali ke Dashboard</span>
      </button>

      <header className="mb-10">
        <h2 className="text-3xl font-black text-white tracking-tighter mb-3 uppercase italic">Hubungkan <span className="text-orange-500">Toko Anda</span></h2>
        <p className="text-zinc-400 text-sm max-w-lg">Pilih marketplace yang ingin Anda integrasikan. Kami menggunakan koneksi enkripsi tingkat tinggi untuk menjamin keamanan data toko Anda.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {platforms.map((p) => (
          <div 
            key={p.id}
            className={`bg-zinc-900 border-2 border-zinc-800 rounded-[2.5rem] p-8 flex flex-col items-center text-center transition-all relative overflow-hidden group ${p.status === 'Ready' ? 'hover:border-orange-500 hover:shadow-2xl hover:shadow-orange-500/10' : 'opacity-60 cursor-not-allowed'}`}
          >
            {p.status === 'Coming Soon' && (
              <div className="absolute top-6 right-6 bg-zinc-800 text-zinc-500 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border border-zinc-700">
                Soon
              </div>
            )}
            
            <div className={`w-20 h-20 rounded-3xl ${p.color} flex items-center justify-center mb-6 shadow-xl relative z-10 group-hover:scale-110 transition-transform duration-500`}>
              <iconify-icon icon={p.icon} className="text-white text-4xl"></iconify-icon>
            </div>

            <h3 className="text-xl font-bold text-white mb-3 tracking-tight">{p.name}</h3>
            <p className="text-xs text-zinc-500 leading-relaxed mb-8 px-2">{p.desc}</p>

            <button 
              disabled={p.status !== 'Ready'}
              className={`w-full py-4 rounded-2xl text-xs font-black uppercase tracking-[0.2em] transition-all ${
                p.status === 'Ready' 
                  ? 'bg-zinc-800 text-white hover:bg-orange-600 shadow-sm' 
                  : 'bg-zinc-950 text-zinc-700'
              }`}
            >
              {p.status === 'Ready' ? 'Hubungkan Sekarang' : 'Mohon Menunggu'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-12 p-6 bg-orange-950/20 border border-orange-900/30 rounded-3xl flex items-start gap-4">
        <iconify-icon icon="solar:shield-check-bold" className="text-orange-500 text-2xl shrink-0"></iconify-icon>
        <div>
          <h4 className="text-sm font-bold text-orange-200 mb-1">Keamanan Data Terjamin</h4>
          <p className="text-xs text-orange-200/60 leading-relaxed">Tokcer AI tidak menyimpan password marketplace Anda. Kami menggunakan OAuth 2.0 yang diakui secara global untuk akses data yang aman dan terbatas hanya pada informasi penjualan serta inventaris.</p>
        </div>
      </div>
    </div>
  );
};

export default StoreIntegrator;
