import React, { useState } from 'react';
import DashboardRevenue from '../dashboard/tabs/RevenueTab.jsx';
import DashboardInventory from '../dashboard/tabs/InventoryTab.jsx';

const TIKTOK_MESSAGES = [
  "AI-nya lagi latian joget pargoy nyari inspirasi hook maut. Biar dia nggak encok pinggang, stopin pakai cara login yuk! 🕺",
  "Waduh, skrip FYP-nya ngumpet di dalem guling! Katanya malu kalau belum kenal. Tarik keluar pakai tombol daftar yuk! 🛌",
  "Maaf, mesin perangkai kata kita tertidur pulas dengerin sound JJ (Jedag Jedug) slowmo. Bangunin pakai tombol Register ya! 😴",
  "Koneksi ke pusat satelit FYP kerasa berat nih. Kayaknya butuh 'tumbal' akun baru. Daftar dulu dong, Kak! 🛸",
  "Otak AI-nya ngebul kebanyakan mikirin penempatan keranjang kuning. Kasih napas bentar nyeduh kopi sambil Kakak bikin akun ya! ☕",
  "Skrip ini berpotensi bikin HP Kakak error saking banyaknya notif pesanan. Tanda tangan (register) dulu dong buat asuransinya! 📜",
  "Lagi sibuk ngelobi algoritma TikTok nih! Biar proposal masuk FYP-nya di-ACC, titip absen (daftar) di sini dulu ya. 💼",
  "AI-nya insecure, takut dibilang SKSD kalau ngasih naskah ke orang asing. Bikin status kita resmi lewat tombol login yuk! 💍",
  "Trauma di-ghosting penonton, AI-nya sekarang minta kepastian. Yuk kasih kepastian pakai email Kakak di menu Register! 👻",
  "Bentar Kak, scriptwriter gaib kita lagi benerin ringlight. Sambil nunggu dia on-camera, mending daftar akun dulu gih! 💡"
];

const MARKETPLACE_MESSAGES = [
  "AI-nya lagi sibuk ngegulung bubble wrap mikirin deskripsi produk. Biar kerjanya makin sat-set, Kakak bikin akun dulu gih! 📦",
  "Takut paket kata-katanya di-retur COD gara-gara alamat pembeli nggak jelas. Tulis alamat (register) dulu yuk Kak di mari! 🚚",
  "Lagi ngeracik pelet online biar pembeli nggak cuma masukin keranjang doang. Masukin mantra 'Login' dulu yuk biar manjur! 🧙‍♂️",
  "Maaf, shift penjaga gudang kosa katanya lagi pergantian. Sambil nunggu yang baru dateng, ngisi buku tamu (daftar) dulu ya Kak! 📋",
  "Wah, ide deskripsi mautnya kejebak macet di lampu merah. Buka jalan tolnya pakai tombol Register yuk! 🚥",
  "Sistem kita lagi laper, butuh asupan data pendaftaran. Suapin satu akun baru dong Kak, biar dia kuat ngetik deskripsi laris! 🍔",
  "AI-nya mau tipes kebanyakan mikirin promo gratis ongkir buat Kakak. Biar cepet sembuh, tolong suntik pakai pendaftaran akun baru ya! 💉",
  "Sistemnya overthinking takut deskripsinya di-copas toko sebelah. Kasih jaminan keamanan pakai cara register dulu yuk! 🔒",
  "Udah nyiapin karpet merah buat review Bintang 5 nih! Tapi tiket masuk ke venue-nya Kakak harus login dulu ya. 🎟️",
  "Timbangan cuan kita agak oleng nih. Bantuin seimbangin pakai berat badan akun baru Kakak yuk, tinggal klik daftar! ⚖️"
];

const INSTAGRAM_MESSAGES = [
  "Caption-nya lagi maskeran dulu biar hasilnya lebih aesthetic dan glowing. Sambil nunggu kering, Kakak bikin akun yuk! 🥒",
  "AI kita lagi semedi di pucuk gunung nyari wangsit buat caption jualan Kakak. Panggil pulang pakai tombol Register ya! 🧘‍♂️",
  "Lagi kena writer's block nih gegara belum ngopi senja. Traktir kopi pakai cara daftar akun yuk, dijamin idenya ngalir deres! 🌅",
  "Duh, ide caption-nya tutup muka pas disorot kamera. Kayaknya dia butuh temen yang udah punya akun deh buat nemenin. 🥺",
  "AI-nya lagi ngorek-ngorek gudang nyari hashtag yang belum basi. Bantuin nyenterin pakai tombol Login dong Kak! 🔦",
  "Sistemnya lagi sibuk ngapus background foto mantan... eh, maksudnya nyiapin caption! Kakak ngisi form daftar dulu aja ya. ✂️",
  "Biar caption-nya se-cool selebgram centang biru, sistem kita lagi pakai kacamata hitam. Yuk kenalan (daftar) dulu sama si cool ini! 😎",
  "Lagi pusing misahin emoji api 🔥 sama emoji nangis 😭 buat diselipin di caption. Hibur AI-nya dengan cara bikin akun yuk! 😵‍💫",
  "Mesin penarik likes-nya lagi mogok kerja minta naik gaji. Sogok pakai pendaftaran akun baru yuk biar mesinnya nyala lagi! 💸",
  "Caption ini mengandung rahasia dapur persaingan olshop. AI-nya cuma mau bisikin ke member resmi. Daftar yuk buat ikutan ngegosip! 🤫"
];

const DashboardPreview = () => {
  const [activeTab, setActiveTab] = useState('tab-dash');
  const [aiFormat, setAiFormat] = useState('TikTok Video');
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiResult, setAiResult] = useState('');

  // Dummy functions for preview components
  const t = (key) => {
    const keys = {
      revenue: "Data Omzet",
      inventory: "Inventory",
      addProduct: "Tambah Produk",
      incomeToday: "Pendapatan Hari Ini",
      activeOrders: "Pesanan Aktif",
      convRate: "Tingkat Konversi",
      orders: "Pesanan",
      processing: "Proses",
      orderId: "Order ID",
      productSold: "Produk",
      platform: "Platform",
      amount: "Nominal",
      status: "Status",
      date: "Tanggal",
      sku: "SKU",
      stock: "Stok",
      price: "Harga",
      runningLow: "Running Low",
      optimal: "Optimal",
      allPlatforms: "Semua Platform",
      omzetFilterAll: "Semua Waktu",
      downloadReport: "Download Laporan",
      revenueDesc: "Visualisasi performa penjualan real-time."
    };
    return keys[key] || key;
  };

  const dummyOrders = [
    { id: '1', order_number: 'TK-12345', customer_name: 'Budi Santoso', platform: 'TikTok', total_amount: 250000, status: 'completed', order_date: new Date().toISOString() },
    { id: '2', order_number: 'SP-99821', customer_name: 'Siti Aminah', platform: 'Shopee', total_amount: 120000, status: 'pending', order_date: new Date().toISOString() },
    { id: '3', order_number: 'SP-77612', customer_name: 'Andi Wijaya', platform: 'Shopee', total_amount: 450000, status: 'completed', order_date: new Date().toISOString() },
  ];

  const dummyProducts = [
    { id: '1', name: 'Kaos Polos Premium', sku: 'KPS-BLK-L', stock: 45, price: 85000, description: 'Bahan cotton combed 30s' },
    { id: '2', name: 'Sepatu Sneakers A1', sku: 'SNR-WHT-42', stock: 8, price: 350000, description: 'Sneakers putih casual' },
    { id: '3', name: 'Jaket Hoodie Urban', sku: 'HOD-GRY-XL', stock: 12, price: 220000, description: 'Bahan fleece tebal' },
  ];

  const handleGenerateAI = (e) => {
    e.preventDefault();
    setIsGenerating(true);
    setAiResult('');
    
    setTimeout(() => {
      let pool = TIKTOK_MESSAGES;
      if (aiFormat === 'Marketplace') pool = MARKETPLACE_MESSAGES;
      if (aiFormat === 'Instagram Feed') pool = INSTAGRAM_MESSAGES;
      
      const randomMsg = pool[Math.floor(Math.random() * pool.length)];
      setAiResult(randomMsg);
      setIsGenerating(false);
    }, 1500);
  };

  return (
    <div className="w-full bg-zinc-900 rounded-[2rem] border border-zinc-800 shadow-xl overflow-hidden flex flex-col md:flex-row min-h-[42rem] md:h-[42rem]">
      <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-zinc-800 bg-black flex flex-col shrink-0 relative">
        <div className="p-3 md:p-4 md:pt-8 w-full overflow-x-auto md:overflow-visible custom-scrollbar">
          <div className="hidden md:block text-xs font-medium text-zinc-500 uppercase tracking-[0.2em] mb-4 px-3">
            Menu Utama
          </div>
          <nav className="flex flex-row md:flex-col gap-2 min-w-max md:min-w-0">
            {[
              { id: 'tab-dash', label: 'Dashboard', icon: 'solar:widget-linear' },
              { id: 'tab-omzet', label: 'Data Omzet', icon: 'solar:chart-square-linear' },
              { id: 'tab-inventory', label: 'Inventory', icon: 'solar:box-linear' },
              { id: 'tab-ai', label: 'AI Generator', icon: 'solar:magic-stick-3-linear' }
            ].map((tab) => (
              <button 
                key={tab.id}
                onClick={() => setActiveTab(tab.id)} 
                className={`sidebar-btn w-auto md:w-full flex items-center gap-3 px-4 md:px-3 py-2.5 rounded-xl text-sm transition-all shrink-0 relative ${activeTab === tab.id ? 'font-medium bg-orange-950/50 text-orange-500 border border-orange-900/50 md:border-0 md:border-l-2 md:border-orange-500' : 'font-normal text-zinc-400 hover:text-white hover:bg-zinc-800 border border-transparent'}`}
              >
                <iconify-icon icon={tab.icon} className="text-lg"></iconify-icon> {tab.label}
              </button>
            ))}
          </nav>

          <div className="hidden md:block mt-10 mb-4 px-3 text-xs font-medium text-zinc-500 uppercase tracking-[0.2em]">
            Fitur Premium
          </div>
          <nav className="hidden md:flex flex-col gap-1.5">
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-normal text-zinc-500 cursor-not-allowed">
              <iconify-icon icon="solar:shield-check-linear" className="text-lg"></iconify-icon> Health Score
            </button>
            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-normal text-zinc-500 cursor-not-allowed">
              <iconify-icon icon="solar:global-linear" className="text-lg"></iconify-icon> Market Intel
            </button>
          </nav>
        </div>
      </aside>
      
      <main className="flex-1 min-w-0 bg-zinc-900 p-5 md:p-8 overflow-y-auto overflow-x-hidden custom-scrollbar relative">
        {activeTab === 'tab-dash' && (
          <div className="relative z-10 animate-in fade-in duration-500">
            <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
              <div>
                <h2 className="text-2xl font-semibold text-white tracking-tight">Overview</h2>
                <p className="text-xs text-zinc-400 mt-1">Pantau performa tokomu detik ini juga.</p>
              </div>
            </header>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group hover:border-orange-500/50 transition-colors shadow-sm">
                <div className="flex items-center gap-3 text-xs font-medium text-zinc-400 mb-3">Total Omzet</div>
                <div className="text-2xl font-semibold text-white tracking-tight">Rp 128.450.000</div>
              </div>
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 relative overflow-hidden group hover:border-amber-500/50 transition-colors shadow-sm">
                <div className="flex items-center gap-3 text-xs font-medium text-zinc-400 mb-3">Profit Bersih</div>
                <div className="text-2xl font-semibold text-amber-500 tracking-tight">Rp 42.120.000</div>
              </div>
            </div>
            <div className="bg-black border border-zinc-800 rounded-2xl p-6 h-56 flex flex-col justify-end gap-2 px-4 relative overflow-hidden">
               <div className="flex items-end justify-between gap-4 h-full">
                  <div className="w-full bg-orange-900/50 h-[30%] rounded-t"></div>
                  <div className="w-full bg-orange-900/50 h-[60%] rounded-t"></div>
                  <div className="w-full bg-orange-500 h-full rounded-t"></div>
                  <div className="w-full bg-orange-900/50 h-[40%] rounded-t"></div>
                  <div className="w-full bg-orange-900/50 h-[50%] rounded-t"></div>
               </div>
            </div>
          </div>
        )}

        {activeTab === 'tab-omzet' && (
          <DashboardRevenue 
            t={t}
            orders={dummyOrders}
            platformFilter="all"
            omzetTimeFilter="all"
            setPlatformFilter={() => {}}
            setOmzetTimeFilter={() => {}}
            showPlatformDropdown={false}
            setShowPlatformDropdown={() => {}}
            showOmzetTimeDropdown={false}
            setShowOmzetTimeDropdown={() => {}}
            handleDownloadReport={() => alert("Silakan daftar untuk mengunduh laporan asli.")}
            handleImportOrders={() => alert("Fitur Import hanya tersedia untuk pengguna terdaftar.")}
          />
        )}

        {activeTab === 'tab-inventory' && (
          <DashboardInventory 
            t={t}
            products={dummyProducts}
            setShowProductModal={() => alert("Silakan daftar untuk menambah produk baru.")}
            handleImportProducts={() => alert("Fitur Import hanya tersedia untuk pengguna terdaftar.")}
          />
        )}

        {activeTab === 'tab-ai' && (
          <div className="relative z-10 animate-in fade-in duration-500">
            <header className="mb-8">
              <h2 className="text-2xl font-semibold text-white tracking-tight flex items-center gap-2">
                AI Content Generator
                <span className="bg-orange-950/50 text-orange-500 px-2 py-0.5 rounded text-[10px] uppercase tracking-widest font-medium border border-orange-900/50">Beta</span>
              </h2>
              <p className="text-sm text-zinc-400 mt-2">Bikin copywriting jualan yang siap narik pembeli pakai AI. Tinggal klik!</p>
            </header>
            
            <div className="max-w-2xl space-y-6">
              <div className="relative bg-black border border-zinc-800 rounded-xl shadow-sm focus-within:border-orange-500 transition duration-300">
                <textarea className="w-full bg-transparent p-4 text-sm text-white focus:outline-none placeholder:text-zinc-600 resize-none" rows="4" placeholder="Ketik deskripsi produk Anda di sini..."></textarea>
              </div>
              
              <div className="space-y-3">
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-widest">Pilih Format Output</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { id: 'TikTok Video', icon: 'solar:video-frame-play-horizontal-linear' },
                    { id: 'Marketplace', icon: 'solar:shop-linear' },
                    { id: 'Instagram Feed', icon: 'solar:camera-linear' }
                  ].map((f) => (
                    <button 
                      key={f.id}
                      onClick={() => { setAiFormat(f.id); setAiResult(''); }}
                      className={`px-4 py-4 rounded-xl text-xs font-medium flex flex-col items-center gap-2 transition-all border-2 ${aiFormat === f.id ? 'bg-orange-950/30 border-orange-500 text-orange-400' : 'bg-black border-zinc-800 text-zinc-500 hover:border-zinc-700'}`}
                    >
                      <iconify-icon icon={f.icon} className="text-2xl"></iconify-icon>
                      {f.id}
                    </button>
                  ))}
                </div>
              </div>
              
              <button 
                onClick={handleGenerateAI}
                disabled={isGenerating}
                className="w-full bg-orange-600 text-white py-4 rounded-xl text-sm font-bold shadow-lg hover:bg-orange-500 transition-all flex justify-center items-center gap-2 border border-orange-500 disabled:opacity-50"
              >
                {isGenerating ? (
                   <><iconify-icon icon="solar:spinner-linear" className="text-lg animate-spin"></iconify-icon> AI lagi nyari wangsit...</>
                ) : (
                  <><iconify-icon icon="solar:magic-stick-3-linear" className="text-lg"></iconify-icon> Generate Magic Content</>
                )}
              </button>

              {aiResult && (
                <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-2xl animate-in fade-in slide-in-from-top-4 duration-500">
                  <div className="flex items-center gap-2 mb-4 text-orange-500 text-[10px] font-black uppercase tracking-widest">
                    <iconify-icon icon="solar:stars-bold" className="text-sm"></iconify-icon> Hasil Generate
                  </div>
                  <p className="text-sm text-zinc-300 leading-relaxed italic font-medium italic">"{aiResult}"</p>
                  <div className="mt-6 pt-6 border-t border-zinc-800 flex flex-col sm:flex-row gap-3">
                    <button onClick={() => window.location.href='#pricing'} className="bg-orange-600 hover:bg-orange-500 text-white px-8 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all shadow-lg shadow-orange-600/20">Daftar Sekarang</button>
                    <button onClick={() => window.location.href='#pricing'} className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-8 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">Lihat Paket</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default DashboardPreview;
