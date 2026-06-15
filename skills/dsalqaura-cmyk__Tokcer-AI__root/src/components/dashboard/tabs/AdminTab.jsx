import React from 'react';

const AdminTab = ({ adminClients, isAdminLoading, handleApproveClient }) => {
  return (
    <div className="relative z-10 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header>
        <h2 className="text-2xl font-semibold text-white tracking-tight">Dashboard Internal Admin</h2>
        <p className="text-xs text-zinc-400 mt-1">Review dan aktivasi pendaftaran dari Partner.</p>
      </header>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/5 text-[10px] text-zinc-500 font-black uppercase tracking-widest border-b border-zinc-800/50">
                <th className="px-6 py-4">Toko / Partner</th>
                <th className="px-6 py-4">Paket / Bayar</th>
                <th className="px-6 py-4">Bukti</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {adminClients.length === 0 && !isAdminLoading && (
                <tr>
                  <td colSpan="5" className="py-20 text-center text-zinc-500 italic">Belum ada data pendaftaran.</td>
                </tr>
              )}
              {adminClients.map((client) => (
                <tr key={client.id} className="border-b border-zinc-800/30 hover:bg-white/[0.01] transition-colors">
                  <td className="px-6 py-4">
                    <div className="text-sm font-bold text-white">{client.shop_name}</div>
                    <div className="text-[10px] text-zinc-500">{client.email}</div>
                    <div className="text-[9px] text-orange-500 font-black mt-1 uppercase tracking-tighter">BY: {client.partners?.full_name || 'Partner Unknown'}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-xs font-bold text-zinc-300 uppercase">{client.plan}</div>
                    <div className="text-[10px] text-zinc-500 uppercase">{client.payment_method}</div>
                  </td>
                  <td className="px-6 py-4">
                    {client.payment_proof_url ? (
                      <button className="text-orange-500 hover:underline text-[10px] font-bold" onClick={() => window.open(client.payment_proof_url)}>Lihat Bukti</button>
                    ) : (
                      <span className="text-zinc-600 text-[10px]">No File</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-[9px] font-black uppercase border ${
                      client.status === 'active' ? 'text-emerald-500 border-emerald-500/20 bg-emerald-500/10' : 'text-amber-500 border-amber-500/20 bg-amber-500/10'
                    }`}>
                      {client.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    {client.status === 'pending' && (
                      <button 
                        onClick={() => handleApproveClient(client.id, client.email, client.shop_name)}
                        disabled={isAdminLoading}
                        className="bg-orange-600 hover:bg-orange-500 text-white px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest shadow-lg shadow-orange-600/20 transition-all"
                      >
                        Approve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminTab;
