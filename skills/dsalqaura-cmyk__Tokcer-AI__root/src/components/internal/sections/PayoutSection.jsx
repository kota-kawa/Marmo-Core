import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase.js';

const PayoutSection = ({ t }) => {
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const fetchPayouts = async () => {
    setLoading(true);
    // 1. Fetch partners yang punya omzet
    const { data: partnersData, error } = await supabase
      .from('partners')
      .select('id, full_name, bank_name, bank_account, whatsapp, total_omzet, created_at')
      .gt('total_omzet', 0);

    // 2. Fetch riwayat payouts untuk dikurangi
    const { data: allPayouts } = await supabase
      .from('payouts')
      .select('partner_id, amount, status')
      .eq('status', 'paid');

    if (!error && partnersData) {
      const generatedPending = [];
      
      partnersData.forEach(p => {
        const partnerPayouts = (allPayouts || []).filter(pay => pay.partner_id === p.id);
        const totalPaid = partnerPayouts.reduce((sum, pay) => sum + (Number(pay.amount) || 0), 0);
        const pendingBalance = Math.max(0, p.total_omzet - totalPaid);

        if (pendingBalance > 0) {
          generatedPending.push({
            id: p.id, // ID partner sebagai referensi checkbox
            amount: pendingBalance,
            created_at: new Date().toISOString(),
            status: 'pending',
            partners: {
              full_name: p.full_name,
              bank_name: p.bank_name,
              bank_account: p.bank_account,
              whatsapp: p.whatsapp
            }
          });
        }
      });
      
      setPayouts(generatedPending.sort((a, b) => b.amount - a.amount));
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPayouts();
  }, []);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const pendingIds = payouts.filter(p => p.status === 'pending').map(p => p.id);
      setSelectedIds(pendingIds);
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(itemId => itemId !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleApproveSelected = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Konfirmasi pembayaran untuk ${selectedIds.length} partner? Saldo pending akan otomatis terpotong.`)) return;

    setIsProcessing(true);
    try {
      const payoutsToInsert = selectedIds.map(partnerId => {
        const pData = payouts.find(p => p.id === partnerId);
        const monthNames = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
        const periodStr = `${monthNames[new Date().getMonth()]} ${new Date().getFullYear()}`;
        return {
          partner_id: partnerId,
          amount: pData.amount,
          status: 'paid',
          period: periodStr
        };
      });

      const { error } = await supabase
        .from('payouts')
        .insert(payoutsToInsert);

      if (error) throw error;
      
      alert(`Berhasil mencatat ${selectedIds.length} pembayaran baru.`);
      setSelectedIds([]);
      fetchPayouts();
    } catch (err) {
      console.error(err);
      alert('Gagal mengonfirmasi pembayaran: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-black text-white uppercase tracking-tight">Pembayaran Partner</h2>
          <p className="text-sm text-zinc-500 font-medium">Manajemen pencairan komisi (Payouts)</p>
        </div>
        <button 
          onClick={handleApproveSelected}
          disabled={selectedIds.length === 0 || isProcessing}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg ${
            selectedIds.length > 0 
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/20 hover:scale-105' 
              : 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700'
          }`}
        >
          <iconify-icon icon={isProcessing ? "solar:hourglass-bold-duotone" : "solar:check-circle-bold"}></iconify-icon>
          {isProcessing ? 'Memproses...' : `Approve Terpilih (${selectedIds.length})`}
        </button>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-zinc-500">Loading data...</div>
        ) : payouts.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <iconify-icon icon="solar:wallet-money-linear" className="text-3xl text-zinc-500"></iconify-icon>
            </div>
            <p className="text-zinc-400">Belum ada riwayat pembayaran.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-400">
              <thead className="text-[10px] uppercase tracking-widest text-zinc-500 bg-zinc-950/50 border-b border-zinc-800">
                <tr>
                  <th className="py-4 px-6 w-12 text-center">
                    <input 
                      type="checkbox" 
                      onChange={handleSelectAll}
                      checked={selectedIds.length > 0 && selectedIds.length === payouts.filter(p => p.status === 'pending').length}
                      className="rounded border-zinc-700 bg-zinc-800 text-orange-500 focus:ring-orange-500/50"
                    />
                  </th>
                  <th className="py-4 px-6">Partner</th>
                  <th className="py-4 px-6">Informasi Bank</th>
                  <th className="py-4 px-6">Jumlah</th>
                  <th className="py-4 px-6">Tanggal</th>
                  <th className="py-4 px-6">Status</th>
                </tr>
              </thead>
              <tbody>
                {payouts.map((p) => (
                  <tr key={p.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors group">
                    <td className="py-4 px-6 text-center">
                      {p.status === 'pending' ? (
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(p.id)}
                          onChange={() => handleSelectOne(p.id)}
                          className="rounded border-zinc-700 bg-zinc-800 text-orange-500 focus:ring-orange-500/50"
                        />
                      ) : (
                        <iconify-icon icon="solar:check-circle-bold" className="text-emerald-500"></iconify-icon>
                      )}
                    </td>
                    <td className="py-4 px-6">
                      <div className="font-bold text-white mb-1">{p.partners?.full_name || 'Partner Tidak Ditemukan'}</div>
                      <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                        <iconify-icon icon="ic:baseline-whatsapp"></iconify-icon>
                        {p.partners?.whatsapp || '-'}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="font-bold text-blue-400">{p.partners?.bank_name || 'Bank -'}</div>
                      <div className="text-zinc-400 font-mono text-[10px]">{p.partners?.bank_account || 'No Rek -'}</div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="font-black text-white">Rp {new Intl.NumberFormat('id-ID').format(p.amount)}</div>
                    </td>
                    <td className="py-4 px-6">
                      {new Date(p.created_at).toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' })}
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border ${
                        p.status === 'paid'
                          ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                          : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PayoutSection;
