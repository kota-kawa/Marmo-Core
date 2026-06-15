import React, { useState } from 'react';
import { supabase } from '../../lib/supabase';

const PartnerModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    const formData = new FormData(e.target);
    const promo_methods = formData.getAll('promo_method[]');
    
    const data = {
      nama: formData.get('nama'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      media_link: formData.get('media_link'),
      niche: formData.get('niche'),
      followers: formData.get('followers'),
      promo_methods: promo_methods,
      promo_strategy: formData.get('promo_strategy')
    };

    const { error } = await supabase.from('partner_applications').insert([data]);

    setLoading(false);

    if (error) {
      console.error(error);
      if (error.code === '23505') {
        setStatus('Email sudah terdaftar sebagai partner!');
      } else {
        setStatus('Terjadi kesalahan, silakan coba lagi.');
      }
    } else {
      setStatus('success');
      setTimeout(() => {
        onClose();
        setStatus(null);
        e.target.reset();
      }, 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative bg-zinc-900 w-full max-w-md p-6 md:p-8 rounded-2xl shadow-2xl border border-zinc-800 m-4 max-h-[90vh] overflow-y-auto custom-scrollbar">
        <button onClick={onClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors">
          <iconify-icon icon="solar:close-circle-linear" className="text-2xl"></iconify-icon>
        </button>
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/30 border border-amber-900/50 mb-4">
            <span className="flex h-1.5 w-1.5 rounded-full bg-amber-500 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            </span>
            <span className="text-[10px] font-medium text-amber-500 uppercase tracking-widest">
              Mitra Resmi
            </span>
          </div>
          <h3 className="text-2xl font-semibold text-white tracking-tight">Become a Partner</h3>
          <p className="text-sm text-zinc-400 mt-2 leading-relaxed">
            Perluas network Anda sebagai Exclusive Partner kami dan amankan akses ke revenue stream khusus dari setiap pertumbuhan kami.
          </p>
        </div>
        
        {status === 'success' ? (
          <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-xl p-6 text-center">
            <div className="w-12 h-12 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <iconify-icon icon="solar:check-circle-bold" className="text-2xl"></iconify-icon>
            </div>
            <h4 className="text-lg font-semibold text-white mb-2">Data Terkirim!</h4>
            <p className="text-sm text-zinc-400">Terima kasih telah mendaftar. Silakan <strong>cek email Anda</strong> untuk menyetujui Skema Komisi & mengaktifkan akun Partner Anda.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {status && typeof status === 'string' && status !== 'success' && (
              <div className="bg-rose-500/10 border border-rose-500/50 text-rose-500 p-3 rounded-lg text-sm text-center">
                {status}
              </div>
            )}
            
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Nama Lengkap <span className="text-rose-500">*</span>
              </label>
              <input type="text" name="nama" required placeholder="Cth: Budi S." className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all" />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Email Aktif <span className="text-rose-500">*</span>
              </label>
              <input type="email" name="email" required placeholder="budi@gmail.com" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all" />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                No. WhatsApp Aktif <span className="text-rose-500">*</span>
              </label>
              <input type="tel" name="phone" required placeholder="0812xxxxxx" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all" />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Link Media Utama (IG/TikTok/YT/Web) <span className="text-rose-500">*</span>
              </label>
              <input type="url" name="media_link" required placeholder="https://instagram.com/..." className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all" />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Niche Konten <span className="text-rose-500">*</span>
                </label>
                <select name="niche" required defaultValue="" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all appearance-none cursor-pointer">
                  <option value="" disabled>Pilih Niche</option>
                  <option value="Bisnis/Edukasi">Bisnis / Edukasi</option>
                  <option value="Teknologi/Gadget">Teknologi / Gadget</option>
                  <option value="Lifestyle/Fashion">Lifestyle / Fashion</option>
                  <option value="Review Produk">Review Produk</option>
                  <option value="Lainnya">Lainnya</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Estimasi Followers <span className="text-rose-500">*</span>
                </label>
                <select name="followers" required defaultValue="" className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all appearance-none cursor-pointer">
                  <option value="" disabled>Pilih Jumlah</option>
                  <option value="< 10k">&lt; 10k</option>
                  <option value="10k - 50k">10k - 50k</option>
                  <option value="50k - 100k">50k - 100k</option>
                  <option value="> 100k">&gt; 100k</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2">
                Cara Promosi <span className="text-rose-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="flex items-center gap-2 p-2 border border-zinc-700 rounded-lg cursor-pointer hover:bg-zinc-800 bg-zinc-800/50 transition-colors">
                  <input type="checkbox" name="promo_method[]" value="WA Blast" className="rounded bg-zinc-900 border-zinc-600 text-amber-500 focus:ring-amber-500" />
                  <span className="text-sm text-zinc-300">WA Blast</span>
                </label>
                <label className="flex items-center gap-2 p-2 border border-zinc-700 rounded-lg cursor-pointer hover:bg-zinc-800 bg-zinc-800/50 transition-colors">
                  <input type="checkbox" name="promo_method[]" value="Social Media" className="rounded bg-zinc-900 border-zinc-600 text-amber-500 focus:ring-amber-500" />
                  <span className="text-sm text-zinc-300">Social Media</span>
                </label>
                <label className="flex items-center gap-2 p-2 border border-zinc-700 rounded-lg cursor-pointer hover:bg-zinc-800 bg-zinc-800/50 transition-colors">
                  <input type="checkbox" name="promo_method[]" value="Paid Ads" className="rounded bg-zinc-900 border-zinc-600 text-amber-500 focus:ring-amber-500" />
                  <span className="text-sm text-zinc-300">Paid Ads</span>
                </label>
                <label className="flex items-center gap-2 p-2 border border-zinc-700 rounded-lg cursor-pointer hover:bg-zinc-800 bg-zinc-800/50 transition-colors">
                  <input type="checkbox" name="promo_method[]" value="Community" className="rounded bg-zinc-900 border-zinc-600 text-amber-500 focus:ring-amber-500" />
                  <span className="text-sm text-zinc-300">Community</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Strategi Promosi (Min. 50 karakter) <span className="text-rose-500">*</span>
              </label>
              <textarea name="promo_strategy" required minLength="50" rows="3" placeholder="Ceritakan bagaimana cara kamu mempromosikan Tokcer AI..." className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white placeholder:text-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 transition-all resize-none custom-scrollbar"></textarea>
            </div>

            <button type="submit" disabled={loading} className="w-full flex items-center justify-center gap-2 bg-amber-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-amber-500 transition-all shadow-md mt-4 border border-amber-500 disabled:opacity-70 disabled:cursor-not-allowed">
              {loading && <iconify-icon icon="solar:spinner-linear" className="animate-spin text-lg"></iconify-icon>}
              {loading ? 'Mengirim Data...' : 'Join the Ecosystem'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default PartnerModal;
