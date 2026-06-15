import React from 'react';

const InventoryTab = ({ 
  t, 
  products, 
  setShowProductModal,
  handleImportProducts
}) => {
  const safeProducts = Array.isArray(products) ? products : [];

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target.result;
      const lines = text.split('\n');
      const headers = lines[0].split(',');
      const rows = lines.slice(1).filter(line => line.trim() !== '').map(line => {
        const values = line.split(',');
        const obj = {};
        headers.forEach((header, i) => {
          const key = header.trim();
          const val = values[i]?.trim();
          obj[key] = val;
        });
        return obj;
      });
      
      if (handleImportProducts) {
        handleImportProducts(rows);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="relative z-10 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">{t('inventory')} & Catalog</h2>
          <p className="text-xs text-zinc-400 mt-1">{t('invDesc') || 'Manage your product stock across all platforms.'}</p>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <a 
            href="/templates/product_template.csv" 
            download 
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[10px] font-bold px-4 py-2 rounded-lg transition-all flex items-center justify-center gap-2 border border-zinc-700 shadow-sm"
          >
            <iconify-icon icon="solar:download-minimalistic-linear" className="text-base"></iconify-icon>
            TEMPLATE
          </a>
          <label className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[10px] font-bold px-4 py-2 rounded-lg transition-all flex items-center justify-center gap-2 border border-zinc-700 shadow-sm cursor-pointer">
            <iconify-icon icon="solar:upload-minimalistic-linear" className="text-base"></iconify-icon>
            IMPORT CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleFileUpload} />
          </label>
          <button onClick={() => setShowProductModal(true)} className="bg-orange-600 hover:bg-orange-500 text-white text-[10px] font-black uppercase tracking-widest px-4 py-2 rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-orange-600/20">
            <iconify-icon icon="solar:add-circle-linear" className="text-base"></iconify-icon> 
            {t('addProduct')}
          </button>
        </div>
      </header>
      
      <div className="border border-zinc-800 rounded-3xl overflow-hidden bg-zinc-900 shadow-xl w-full">
        <div className="overflow-x-auto custom-scrollbar">
          <div className="min-w-[800px]">
            <div className="grid grid-cols-12 gap-4 p-5 bg-black/50 text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] border-b border-zinc-800">
              <div className="col-span-5">{t('productSold')}</div>
              <div className="col-span-2">{t('sku')}</div>
              <div className="col-span-2 text-right">{t('price')}</div>
              <div className="col-span-1 text-right">{t('stock')}</div>
              <div className="col-span-2 text-right">{t('status')}</div>
            </div>
            <div className="divide-y divide-zinc-800/50">
              {safeProducts.length > 0 ? safeProducts.map((p) => (
                <div key={p.id} className="grid grid-cols-12 gap-4 p-5 items-center text-sm text-zinc-400 hover:bg-zinc-800/30 transition-all group">
                  <div className="col-span-5 flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center text-zinc-500 group-hover:text-orange-500 group-hover:border-orange-500/30 transition-all border border-zinc-700 shrink-0">
                      <iconify-icon icon="solar:box-bold-duotone" className="text-2xl"></iconify-icon>
                    </div>
                    <div>
                      <div className="font-bold text-white group-hover:text-orange-500 transition-colors truncate max-w-[200px]">{p.name}</div>
                      <div className="text-[10px] text-zinc-500 mt-0.5 truncate max-w-[200px]">{p.description || 'No description'}</div>
                    </div>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[10px] font-mono text-zinc-500 bg-zinc-800/50 px-2 py-1 rounded border border-zinc-700/50">{p.sku || 'N/A'}</span>
                  </div>
                  <div className="col-span-2 text-right text-white font-bold">
                    Rp {Number(p.price || 0).toLocaleString('id-ID')}
                  </div>
                  <div className="col-span-1 text-right text-white font-black">{p.stock}</div>
                  <div className="col-span-2 text-right flex justify-end">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${
                      p.stock > 10 ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 
                      p.stock > 0 ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                    }`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        p.stock > 10 ? 'bg-emerald-500' : 
                        p.stock > 0 ? 'bg-amber-500' : 'bg-rose-500 animate-pulse'
                      }`}></div> 
                      {p.stock > 10 ? t('optimal') : p.stock > 0 ? t('runningLow') : t('outOfStock')}
                    </span>
                  </div>
                </div>
              )) : (
                <div className="py-24 text-center">
                   <iconify-icon icon="solar:box-linear" className="text-4xl text-zinc-800 mb-4"></iconify-icon>
                   <p className="text-sm text-zinc-600 italic font-medium">Belum ada katalog produk. Silakan tambah atau import.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InventoryTab;
