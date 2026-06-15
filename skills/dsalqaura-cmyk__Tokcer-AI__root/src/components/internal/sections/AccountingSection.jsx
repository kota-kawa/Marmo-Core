import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase.js';

const AccountingSection = ({ t }) => {
  const [usdRate, setUsdRate] = useState(17300);
  const [showIncomeModal, setShowIncomeModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false);

  // State untuk Data
  const [incomes, setIncomes] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [kpis, setKpis] = useState({ grossOmzet: 0, netProfit: 0, subscribers: 0, arpu: 0 });

  // State untuk Form Income
  const [incomeSource, setIncomeSource] = useState('organic');
  const [incomePlan, setIncomePlan] = useState('pro');
  const [incomePlanType, setIncomePlanType] = useState('monthly');
  const [incomeAmount, setIncomeAmount] = useState(499000);
  const [periodStart, setPeriodStart] = useState(new Date().toISOString().split('T')[0]);
  const [periodEnd, setPeriodEnd] = useState(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);

  // Auto-update harga berdasarkan pilihan paket
  useEffect(() => {
    if (incomePlan === 'pro') setIncomeAmount(499000);
    else if (incomePlan === 'elite') setIncomeAmount(999000);
    else if (incomePlan === 'ultimate') setIncomeAmount(1999000);
  }, [incomePlan]);

  // State untuk Form Expense
  const [expenseCategory, setExpenseCategory] = useState('web_hosting');
  const [expenseVendor, setExpenseVendor] = useState('');
  const [expenseAmount, setExpenseAmount] = useState(0);
  const [expenseBillingCycle, setExpenseBillingCycle] = useState('monthly');

  // Fungsi Tarik Data & Hitung KPI
  const fetchAccountingData = async () => {
    try {
      // 1. Tarik Data Incomes
      const { data: incomeData, error: incomeError } = await supabase
        .from('income_transactions')
        .select('*')
        .order('date', { ascending: false });
      
      if (incomeError) throw incomeError;
      setIncomes(incomeData || []);

      // 2. Tarik Data Expenses
      const { data: expenseData, error: expenseError } = await supabase
        .from('infra_costs')
        .select('*')
        .order('date', { ascending: false });
      
      if (expenseError) throw expenseError;
      setExpenses(expenseData || []);

      // 3. Ambil jumlah subscriber aktif riil dari tabel clients (hindari duplikasi dari income_transactions)
      const { count: activeSubscriberCount } = await supabase
        .from('clients')
        .select('id', { count: 'exact', head: true })
        .eq('status', 'active')
        .in('plan', ['pro', 'elite', 'ultimate']); // hanya user berbayar

      // 4. Hitung KPI (Logika Spek)
      const totalGross = (incomeData || []).reduce((acc, curr) => acc + curr.gross_amount, 0);
      const totalFee = (incomeData || []).reduce((acc, curr) => acc + (curr.midtrans_fee || 0), 0);
      const totalInfra = (expenseData || []).reduce((acc, curr) => acc + curr.amount_idr, 0);
      
      const netProfit = totalGross - totalFee - totalInfra;
      const subscribers = activeSubscriberCount || 0;
      const arpu = subscribers > 0 ? totalGross / subscribers : 0;

      setKpis({
        grossOmzet: totalGross,
        netProfit,
        subscribers,
        arpu
      });

    } catch (error) {
      console.error("Error fetching accounting data:", error.message);
    }
  };

  useEffect(() => {
    fetchAccountingData();
  }, []);

  // Fungsi Simpan Income
  const handleSaveIncome = async () => {
    const midtransFee = Math.round(incomeAmount * 0.007); // Simulasi 0.7% QRIS/VA
    
    const { error } = await supabase.from('income_transactions').insert([{
      source: incomeSource,
      plan: incomePlan,
      plan_type: incomePlanType,
      gross_amount: parseInt(incomeAmount),
      period_start: periodStart,
      period_end: periodEnd,
      midtrans_fee: midtransFee,
      date: new Date().toISOString().split('T')[0]
    }]);

    if (error) {
      alert("Gagal simpan: " + error.message);
    } else {
      alert("Transaksi Income Berhasil Disimpan!");
      setShowIncomeModal(false);
      fetchAccountingData();
    }
  };

  // Fungsi Simpan Expense
  const handleSaveExpense = async () => {
    const { error } = await supabase.from('infra_costs').insert([{
      category: expenseCategory,
      vendor: expenseVendor,
      amount_idr: parseInt(expenseAmount),
      billing_cycle: expenseBillingCycle,
      date: new Date().toISOString().split('T')[0]
    }]);

    if (error) {
      alert("Gagal simpan: " + error.message);
    } else {
      alert("Biaya Berhasil Dicatat!");
      setShowExpenseModal(false);
      fetchAccountingData();
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
      {/* Header Config */}
      <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 backdrop-blur-xl">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-500">Global Config</span>
            <h2 className="text-3xl font-black text-white tracking-tighter mt-1">Internal Accounting</h2>
          </div>
          <div className="flex items-center gap-3 bg-black/40 p-2 rounded-2xl border border-zinc-800">
            <span className="text-xs font-bold text-zinc-500 px-2">USD/IDR Rate:</span>
            <input 
              type="number" 
              value={usdRate} 
              onChange={(e) => setUsdRate(e.target.value)}
              className="bg-zinc-900 text-white font-black text-sm w-24 p-2 rounded-xl border border-zinc-700 focus:outline-none focus:border-blue-500 transition-all"
            />
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 backdrop-blur-xl">
          <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Total Gross Omzet</p>
          <h3 className="text-2xl font-black text-white tracking-tighter">Rp {kpis.grossOmzet.toLocaleString('id-ID')}</h3>
          <p className="text-[10px] text-zinc-600 mt-1 font-bold">Bulan Ini</p>
        </div>
        <div className="bg-emerald-500/10 p-6 rounded-[2rem] border border-emerald-500/10 backdrop-blur-xl">
          <p className="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-2">Net Profit</p>
          <h3 className="text-2xl font-black text-emerald-400 tracking-tighter">Rp {kpis.netProfit.toLocaleString('id-ID')}</h3>
          <p className="text-[10px] text-emerald-500/60 mt-1 font-bold">Margin: {kpis.grossOmzet > 0 ? Math.round((kpis.netProfit / kpis.grossOmzet) * 100) : 0}%</p>
        </div>
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 backdrop-blur-xl">
          <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Subscribers Aktif</p>
          <h3 className="text-2xl font-black text-white tracking-tighter">{kpis.subscribers}</h3>
          <p className="text-[10px] text-zinc-600 mt-1 font-bold">User Berbayar</p>
        </div>
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 backdrop-blur-xl">
          <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">ARPU</p>
          <h3 className="text-2xl font-black text-white tracking-tighter">Rp {Math.round(kpis.arpu).toLocaleString('id-ID')}</h3>
          <p className="text-[10px] text-zinc-600 mt-1 font-bold">Average Revenue Per User</p>
        </div>
      </div>

      {/* Tables Grid */}
      <div className="grid grid-cols-1 gap-8">
        
        {/* Income Transactions */}
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800">
          <div className="flex justify-between items-center mb-6">
            <div>
              <span className="text-[10px] font-black uppercase tracking-wider text-emerald-500">Income Module</span>
              <h3 className="text-xl font-black text-white tracking-tight mt-1">Income Transactions</h3>
            </div>
            <button onClick={() => setShowIncomeModal(true)} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-black uppercase tracking-widest rounded-xl transition-all">
              + Tambah Transaksi
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-2">
              <thead>
                <tr className="text-zinc-600 text-[10px] font-black uppercase tracking-widest">
                  <th className="p-4">Tanggal</th>
                  <th className="p-4">Source</th>
                  <th className="p-4">Plan</th>
                  <th className="p-4">Gross Amount</th>
                  <th className="p-4">Net After COGS</th>
                </tr>
              </thead>
              <tbody>
                {incomes.length > 0 ? incomes.map(item => (
                  <tr key={item.id} className="bg-zinc-950/50 rounded-2xl border border-zinc-800">
                    <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800 text-xs font-bold text-white">{item.date}</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-white uppercase font-black">{item.source}</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-zinc-400 uppercase">{item.plan} ({item.plan_type})</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-white font-black">Rp {item.gross_amount.toLocaleString('id-ID')}</td>
                    <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800 text-xs text-emerald-400 font-black">Rp {item.net_after_cogs.toLocaleString('id-ID')}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" className="py-10 text-center text-zinc-600 italic text-sm">Belum ada data transaksi masuk.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Infra Costs */}
        <div className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800">
          <div className="flex justify-between items-center mb-6">
            <div>
              <span className="text-[10px] font-black uppercase tracking-wider text-red-500">Expense Module</span>
              <h3 className="text-xl font-black text-white tracking-tight mt-1">Infrastructure Costs</h3>
            </div>
            <button onClick={() => setShowExpenseModal(true)} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-black uppercase tracking-widest rounded-xl border border-zinc-700 transition-all">
              + Catat Biaya
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-2">
              <thead>
                <tr className="text-zinc-600 text-[10px] font-black uppercase tracking-widest">
                  <th className="p-4">Tanggal</th>
                  <th className="p-4">Kategori</th>
                  <th className="p-4">Vendor</th>
                  <th className="p-4">Nominal (IDR)</th>
                  <th className="p-4">Siklus</th>
                </tr>
              </thead>
              <tbody>
                {expenses.length > 0 ? expenses.map(item => (
                  <tr key={item.id} className="bg-zinc-950/50 rounded-2xl border border-zinc-800">
                    <td className="p-4 rounded-l-2xl border-l border-y border-zinc-800 text-xs font-bold text-white">{item.date}</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-white font-bold uppercase">{item.category}</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-zinc-400">{item.vendor}</td>
                    <td className="p-4 border-y border-zinc-800 text-xs text-white font-black">Rp {item.amount_idr.toLocaleString('id-ID')}</td>
                    <td className="p-4 rounded-r-2xl border-r border-y border-zinc-800 text-xs text-zinc-500 font-bold uppercase">{item.billing_cycle}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="5" className="py-10 text-center text-zinc-600 italic text-sm">Belum ada data pengeluaran.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Modal Income */}
      {showIncomeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-zinc-900/90 border border-white/10 rounded-[2rem] p-8 w-full max-w-md text-white relative shadow-2xl">
            <button onClick={() => setShowIncomeModal(false)} className="absolute top-6 right-6 text-white/60 hover:text-white">
              <iconify-icon icon="solar:close-circle-bold-duotone" className="text-2xl"></iconify-icon>
            </button>
            <div className="mb-6">
              <span className="text-[10px] font-black uppercase tracking-wider text-emerald-500">Income Module</span>
              <h3 className="text-xl font-black mt-1">Tambah Transaksi</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Source</label>
                <select value={incomeSource} onChange={(e) => setIncomeSource(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1">
                  <option value="organic">organic</option>
                  <option value="partner">partner</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Plan</label>
                <select value={incomePlan} onChange={(e) => setIncomePlan(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1">
                  <option value="pro">pro</option>
                  <option value="elite">elite</option>
                  <option value="ultimate">ultimate</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Gross Amount</label>
                <input type="number" value={incomeAmount} onChange={(e) => setIncomeAmount(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1" />
              </div>
              <button onClick={handleSaveIncome} className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-black uppercase tracking-widest rounded-xl transition-all">
                Simpan Transaksi
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Expense */}
      {showExpenseModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-zinc-900/90 border border-white/10 rounded-[2rem] p-8 w-full max-w-md text-white relative shadow-2xl">
            <button onClick={() => setShowExpenseModal(false)} className="absolute top-6 right-6 text-white/60 hover:text-white">
              <iconify-icon icon="solar:close-circle-bold-duotone" className="text-2xl"></iconify-icon>
            </button>
            <div className="mb-6">
              <span className="text-[10px] font-black uppercase tracking-wider text-red-500">Expense Module</span>
              <h3 className="text-xl font-black mt-1">Catat Biaya Infra</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Kategori</label>
                <select value={expenseCategory} onChange={(e) => setExpenseCategory(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1">
                  <option value="web_hosting">web_hosting</option>
                  <option value="ai_credit">ai_credit</option>
                  <option value="database">database</option>
                  <option value="email_service">email_service</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Vendor</label>
                <input type="text" value={expenseVendor} onChange={(e) => setExpenseVendor(e.target.value)} placeholder="Nama Vendor" className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1" />
              </div>
              <div>
                <label className="text-[10px] font-black uppercase text-zinc-500">Nominal (IDR)</label>
                <input type="number" value={expenseAmount} onChange={(e) => setExpenseAmount(e.target.value)} className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-sm text-white mt-1" />
              </div>
              <button onClick={handleSaveExpense} className="w-full py-3 bg-red-600 hover:bg-red-700 text-white text-xs font-black uppercase tracking-widest rounded-xl transition-all">
                Simpan Biaya
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountingSection;
