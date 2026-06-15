import React from 'react';

const AccountTab = ({ 
  t, 
  lang, 
  securityMessage, 
  handleUpdatePassword, 
  newPassword, 
  setNewPassword, 
  confirmPassword, 
  setConfirmPassword, 
  isUpdatingPassword,
  profile,
  user,
  clientData
}) => {
  return (
    <div className="relative z-10 animate-in fade-in duration-500 max-w-md">
      <header className="mb-8">
        <h2 className="text-2xl font-semibold text-white tracking-tight">{lang === 'id' ? 'Informasi Akun' : 'Account Information'}</h2>
        <p className="text-xs text-zinc-400 mt-1">
          {lang === 'id' ? 'Kelola profil dan keamanan akun Anda.' : 'Manage your profile and account security.'}
        </p>
      </header>

      {/* GAP 2: Informasi Akun */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-orange-500/20 to-amber-500/10 flex items-center justify-center border border-orange-500/30 shrink-0">
            <span className="text-2xl font-black text-orange-500">{profile?.full_name?.charAt(0)?.toUpperCase() || clientData?.shop_name?.charAt(0)?.toUpperCase() || 'U'}</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white truncate">{profile?.full_name || clientData?.shop_name || 'User'}</h3>
            <p className="text-xs text-zinc-400 truncate">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-6 border-t border-zinc-800">
          <div>
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">{lang === 'id' ? 'Paket Aktif' : 'Active Plan'}</p>
            <p className="text-sm font-bold text-white capitalize">{profile?.subscription_plan || clientData?.plan || 'Starter'}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Status</p>
            <div className="flex items-center gap-1.5">
               <div className={`w-2 h-2 rounded-full ${clientData?.status === 'active' || clientData?.status === 'paid' ? 'bg-emerald-500 animate-pulse' : clientData?.status === 'expired' ? 'bg-rose-500' : 'bg-amber-500'}`}></div>
               <span className="text-sm font-bold text-white capitalize">{clientData?.status || 'Active'}</span>
            </div>
          </div>
          <div className="col-span-2 mt-2">
            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">{lang === 'id' ? 'Tanggal Bergabung' : 'Join Date'}</p>
            <p className="text-sm font-bold text-white">
              {clientData?.created_at ? new Date(clientData.created_at).toLocaleDateString(lang === 'id' ? 'id-ID' : 'en-US', { day: 'numeric', month: 'long', year: 'numeric' }) : '-'}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-orange-950/50 flex items-center justify-center border border-orange-900/50">
            <iconify-icon icon="solar:lock-password-linear" className="text-xl text-orange-500"></iconify-icon>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">{lang === 'id' ? 'Ubah Password' : 'Change Password'}</h3>
            <p className="text-[10px] text-zinc-500">{lang === 'id' ? 'Gunakan kombinasi yang kuat.' : 'Use a strong combination.'}</p>
          </div>
        </div>

        {securityMessage.text && (
          <div className={`p-3 rounded-lg mb-6 text-xs text-center border ${
            securityMessage.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-500' : 'bg-rose-500/10 border-rose-500/50 text-rose-500'
          }`}>
            {securityMessage.text}
          </div>
        )}

        <form onSubmit={handleUpdatePassword} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">{t('passwordLabel')} Baru</label>
            <input 
              type="password" 
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">Konfirmasi Password</label>
            <input 
              type="password" 
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all"
              placeholder="••••••••"
            />
          </div>
          <button 
            type="submit" 
            disabled={isUpdatingPassword}
            className="w-full bg-orange-600 text-white py-3 rounded-xl text-sm font-bold hover:bg-orange-500 transition-all flex justify-center items-center gap-2"
          >
            {isUpdatingPassword ? <iconify-icon icon="solar:spinner-linear" className="animate-spin text-lg"></iconify-icon> : null}
            {isUpdatingPassword ? 'SAVING...' : 'SAVE PASSWORD'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AccountTab;
