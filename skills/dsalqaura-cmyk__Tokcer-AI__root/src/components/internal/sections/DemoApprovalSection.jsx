import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase.js';

const DemoApprovalSection = ({ t }) => {
  const [demos, setDemos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [approving, setApproving] = useState(null);

  useEffect(() => {
    fetchDemos();
  }, []);

  const fetchDemos = async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('demo_applications')
      .select('*')
      .order('created_at', { ascending: false });
    
    if (!error && data) {
      setDemos(data);
    }
    setLoading(false);
  };

  const generateSecurePassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    let password = "TK-";
    for (let i = 0; i < 6; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
  };

  const handleApprove = async (demo) => {
    if (!window.confirm(`Yakin ingin menyetujui akun demo untuk ${demo.name}?`)) return;
    
    setApproving(demo.id);
    const password = generateSecurePassword();

    try {
      const { data, error } = await supabase.rpc('rpc_activate_demo', {
        p_application_id: demo.id,
        p_email: demo.email,
        p_name: demo.name,
        p_password: password
      });

      if (error) throw error;

      // Email sudah dikirim oleh rpc_activate_demo (server-side via net.http_post)
      alert(`✅ Akun Demo ${demo.name} Berhasil Diaktifkan!\n\nEmail: ${demo.email}\nPassword Sementara: ${password}\n\nEmail notifikasi telah dikirimkan ke user.`);
      fetchDemos();
    } catch (err) {
      alert("❌ Gagal aktivasi: " + err.message);
    } finally {
      setApproving(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <iconify-icon icon="solar:user-check-bold-duotone" className="text-indigo-500"></iconify-icon>
          Demo User Approvals
        </h2>
        <button onClick={fetchDemos} className="text-zinc-400 hover:text-white transition-colors">
          <iconify-icon icon="solar:refresh-bold" className={`text-xl ${loading ? 'animate-spin' : ''}`}></iconify-icon>
        </button>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-zinc-950/50 border-b border-zinc-800">
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest">Tanggal</th>
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest">Nama Lengkap</th>
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest">Kontak</th>
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest">Marketplace</th>
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest">Status</th>
                <th className="p-4 text-[10px] font-black uppercase text-zinc-500 tracking-widest text-right">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {demos.length === 0 ? (
                <tr>
                  <td colSpan="6" className="p-8 text-center text-zinc-500 text-sm">Tidak ada permohonan demo saat ini.</td>
                </tr>
              ) : (
                demos.map(demo => (
                  <tr key={demo.id} className="border-b border-zinc-800 hover:bg-zinc-800/30 transition-colors">
                    <td className="p-4">
                      <span className="text-sm text-zinc-300">{new Date(demo.created_at).toLocaleDateString('id-ID')}</span>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-white">{demo.name}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-xs text-zinc-400 font-mono">{demo.email}</p>
                      <p className="text-[10px] text-zinc-500">{demo.phone}</p>
                    </td>
                    <td className="p-4">
                      <span className="text-xs font-medium text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded">{demo.marketplace || '-'}</span>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-[10px] font-bold uppercase tracking-widest ${
                        demo.status === 'approved' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      }`}>
                        {demo.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      {demo.status === 'pending' && (
                        <button 
                          onClick={() => handleApprove(demo)} 
                          disabled={approving === demo.id}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest disabled:opacity-50 transition-all shadow-lg"
                        >
                          {approving === demo.id ? 'Memproses...' : 'Approve'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DemoApprovalSection;
