import React, { useState } from 'react';

const ProductModal = ({ isOpen, onClose, t, onSave }) => {
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const product = {
      name: formData.get('name'),
      platform: formData.get('platform'),
      sku: formData.get('sku'),
      stock: Number(formData.get('stock') || 0),
      price: Number(formData.get('price') || 0),
    };
    setSaving(true);
    try {
      await onSave(product);
      e.target.reset();
      onClose();
    } catch (err) {
      alert('Gagal menyimpan produk: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative bg-zinc-900 w-full max-w-md p-6 md:p-8 rounded-2xl shadow-2xl border border-zinc-800 m-4 max-h-[90vh] overflow-y-auto custom-scrollbar">
        <button onClick={onClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors">
          <iconify-icon icon="solar:close-circle-linear" className="text-2xl"></iconify-icon>
        </button>
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-950/30 border border-orange-900/50 mb-4">
            <span className="text-[10px] font-medium text-orange-500 uppercase tracking-widest">
              {t('inventory')}
            </span>
          </div>
          <h3 className="text-2xl font-semibold text-white tracking-tight">{t('addProduct')}</h3>
          <p className="text-sm text-zinc-400 mt-2 leading-relaxed">
            {t('newProductDesc')}
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('productName')}</label>
              <input type="text" name="name" required placeholder={t('productNamePlaceholder')} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('platform')}</label>
              <select name="platform" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all appearance-none">
                <option value="all">{t('allPlatforms')}</option>
                <option value="shopee">Shopee</option>
                <option value="tiktok">TikTok Shop</option>
              </select>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('sku')}</label>
              <input type="text" name="sku" required placeholder={t('skuPlaceholder')} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all" />
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('initialStock')}</label>
              <input type="number" name="stock" required placeholder="0" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all" />
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">{t('price')} (Rp)</label>
            <input type="number" name="price" required placeholder={t('pricePlaceholder')} className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition-all" />
          </div>

          <button type="submit" disabled={saving} className="w-full flex items-center justify-center gap-2 bg-orange-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-orange-500 transition-all shadow-md mt-6 border border-orange-500 disabled:opacity-50 disabled:cursor-not-allowed">
            {saving ? 'Menyimpan...' : t('saveProduct')}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProductModal;
