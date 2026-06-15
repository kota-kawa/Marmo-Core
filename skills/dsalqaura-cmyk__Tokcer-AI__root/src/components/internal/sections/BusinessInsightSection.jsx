import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase';
import { callAiEngine } from '../../../utils/ai';
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";

const BusinessInsightSection = ({ t }) => {
  const [reports, setReports] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeReport, setActiveReport] = useState(null);
  const [customColumns, setCustomColumns] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newColumn, setNewColumn] = useState({ name: '', key: '' });
  const [partnerCSV, setPartnerCSV] = useState(null);
  const [userNeedsCSV, setUserNeedsCSV] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [reportPeriod, setReportPeriod] = useState('weekly'); // weekly | monthly
  const [isGeneratingPro, setIsGeneratingPro] = useState(false);
  const [proReportHtml, setProReportHtml] = useState(null);

  // Prices Mapping (Hardcoded as requested for logic safety)
  const PLAN_PRICES = {
    starter: 0,
    pro: 499000,
    elite: 999000,
    ultimate: 1999000
  };

  const fetchReports = async () => {
    // In a real scenario, we might have a 'reports' table. 
    // For now, we'll simulate history or just show the "Current Week" generator.
    const { data, error } = await supabase.from('weekly_reports').select('*').order('created_at', { ascending: false });
    if (!error) setReports(data || []);
  };

  useEffect(() => {
    fetchReports();
    // Load custom columns from localStorage for persistence without DB migration yet
    const saved = localStorage.getItem('tokcer_custom_report_cols');
    if (saved) setCustomColumns(JSON.parse(saved));
  }, []);

  const handleFileUpload = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsUploading(true);
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const lines = text.split(/\r?\n/).filter(l => l.trim() !== '');
        if (lines.length < 2) throw new Error("File CSV kosong atau tidak valid");

        const splitCSVLine = (line) => {
          const result = [];
          let cur = "";
          let inQuote = false;
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') inQuote = !inQuote;
            else if (char === ',' && !inQuote) {
              result.push(cur.trim());
              cur = "";
            } else cur += char;
          }
          result.push(cur.trim());
          return result;
        };

        const headers = splitCSVLine(lines[0]);
        const data = lines.slice(1).map(line => {
          const values = splitCSVLine(line);
          const obj = {};
          headers.forEach((h, i) => {
            const cleanH = h.trim();
            if (cleanH) obj[cleanH] = values[i] || '';
          });
          return obj;
        });
        
        if (type === 'partner') setPartnerCSV(data);
        if (type === 'user') setUserNeedsCSV(data);
        alert(`✅ Berhasil memuat ${data.length} data dari CSV ${type.toUpperCase()}`);
      } catch (err) {
        alert("❌ Gagal membaca CSV: " + err.message);
      } finally {
        setIsUploading(false);
      }
    };
    reader.readAsText(file);
  };

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    try {
      // 1. Fetch Latest Configs & Data
      const [configsRes, clientsRes, txRes, payoutsRes] = await Promise.all([
        supabase.from('ai_configs').select('*').or('key.ilike.%price_%,key.eq.target_revenue_monthly'),
        supabase.from('clients').select('*'),
        supabase.from('transactions').select('*').in('status', ['settlement', 'capture']),
        supabase.from('payouts').select('*').eq('status', 'paid')
      ]);

      const configMap = {};
      (configsRes.data || []).forEach(c => configMap[c.key] = c.value);

      // Dynamic Prices (with Hardcoded Fallbacks for Safety)
      const dynamicPrices = {
        starter: Number(configMap['price_starter']) || 0,
        pro: Number(configMap['price_pro']) || 499000,
        elite: Number(configMap['price_elite']) || 999000,
        ultimate: Number(configMap['price_ultimate']) || 1999000
      };
      
      const targetRevenue = Number(configMap['target_revenue_monthly']) || 100000000;
      
      const clients = clientsRes.data || [];
      const transactions = txRes.data || [];
      const payouts = payoutsRes.data || [];

      // 2. Calculations
      const activeSubs = {
        starter: clients.filter(c => c.plan === 'starter' && c.status === 'active').length,
        pro: clients.filter(c => c.plan === 'pro' && c.status === 'active').length,
        elite: clients.filter(c => c.plan === 'elite' && c.status === 'active').length,
        ultimate: clients.filter(c => c.plan === 'ultimate' && c.status === 'active').length,
      };

      const mrr = {
        pro: activeSubs.pro * dynamicPrices.pro,
        elite: activeSubs.elite * dynamicPrices.elite,
        ultimate: activeSubs.ultimate * dynamicPrices.ultimate,
      };

      const totalMrr = mrr.pro + mrr.elite + mrr.ultimate;
      const grossIncome = transactions.reduce((acc, curr) => acc + (Number(curr.gross_amount) || 0), 0);
      const totalPayout = payouts.reduce((acc, curr) => acc + (Number(curr.amount) || 0), 0);
      const netRevenue = grossIncome - totalPayout;

      // 3. AI Analysis
      const progressToTarget = ((grossIncome / targetRevenue) * 100).toFixed(1);

      const prompt = `Analyze this ${reportPeriod} business data for Tokcer AI. 
      Target Revenue: IDR 100,000,000/month. Current Progress: ${progressToTarget}%.
      
      RAW METRICS:
      - Gross Income: IDR ${grossIncome.toLocaleString()}
      - Total MRR: IDR ${totalMrr.toLocaleString()}
      - Net Revenue: IDR ${netRevenue.toLocaleString()}
      - Active Paid Users: ${activeSubs.pro + activeSubs.elite + activeSubs.ultimate}
      
      DYNAMIC INPUT FROM CSV:
      - Partner Data: ${partnerCSV ? JSON.stringify(partnerCSV.slice(0, 5)) : 'No custom partner data'}
      - User/Market Report Data: ${userNeedsCSV ? JSON.stringify(userNeedsCSV.slice(0, 5)) : 'No custom user needs'}
      
      PLEASE PROVIDE EXECUTIVE SUMMARY IN JSON WITH THESE KEYS:
      "financial_health": (Point List based on Part 1),
      "subscriber_movement": (Point List based on Part 2),
      "partner_performance": (Point List based on Part 3),
      "organic_funnel": (Point List based on Part 4),
      "risk_alert": (Point List based on Part 5),
      "strategic_recommendation": (Point List based on Part 6)
      
      Ensure each section contains 3-5 bullet points. Keep it professional and in Bahasa Indonesia.`;
      
      const { text: aiResult, usage } = await callAiEngine("You are a Senior Business Intelligence expert for Tokcer AI SaaS.", prompt, 2048, 0.5);
      const cleanJson = aiResult.replace(/```json|```/g, '').trim();

      // Log AI Usage
      await supabase.from('ai_usage_logs').insert([{
          user_id: 'admin-bypass', 
          feature: 'executive_summary_analysis',
          prompt: prompt,
          response: aiResult,
          tokens_used: 1
      }]);
      let aiNotes = { 
        financial_health: [], 
        subscriber_movement: [], 
        partner_performance: [], 
        organic_funnel: [], 
        risk_alert: [], 
        strategic_recommendation: [] 
      };
      try {
        aiNotes = JSON.parse(cleanJson);
      } catch (e) {
        console.error("AI JSON Parse Error:", e);
        aiNotes = { financial_health: [aiResult], subscriber_movement: [], partner_performance: [], organic_funnel: [], risk_alert: [], strategic_recommendation: [] };
      }

      const newReport = {
        id: Date.now(),
        report_period: reportPeriod,
        report_week: reportPeriod === 'weekly' ? `W${Math.ceil(new Date().getDate() / 7)}` : `M${new Date().getMonth() + 1}`,
        date_start: new Date(Date.now() - (reportPeriod === 'weekly' ? 7 : 30) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        date_end: new Date().toISOString().split('T')[0],
        gross_income_idr: grossIncome,
        total_mrr_idr: totalMrr,
        mrr_pro_idr: mrr.pro,
        mrr_elite_idr: mrr.elite,
        mrr_ultimate_idr: mrr.ultimate,
        total_partner_payout_idr: totalPayout,
        net_revenue_idr: netRevenue,
        active_subscribers_starter: activeSubs.starter,
        active_subscribers_pro: activeSubs.pro,
        active_subscribers_elite: activeSubs.elite,
        active_subscribers_ultimate: activeSubs.ultimate,
        total_active_paid: activeSubs.pro + activeSubs.elite + activeSubs.ultimate,
        progress_target: progressToTarget,
        executive_summary: aiNotes,
        created_at: new Date().toISOString()
      };

      setActiveReport(newReport);
      setReports([newReport, ...reports]);
      
      // Save to DB if table exists (optional, currently simulating persistence via state)
      await supabase.from('weekly_reports').insert([newReport]);

    } catch (err) {
      console.error("Report Generation Error:", err);
      alert("Gagal membuat laporan: " + err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddColumn = () => {
    if (!newColumn.name || !newColumn.key) return;
    const updated = [...customColumns, newColumn];
    setCustomColumns(updated);
    localStorage.setItem('tokcer_custom_report_cols', JSON.stringify(updated));
    setNewColumn({ name: '', key: '' });
    setIsModalOpen(false);
  };

  const exportToCSV = (report) => {
    const headers = [
      'report_week', 'date_start', 'date_end', 'gross_income_idr', 'total_mrr_idr', 
      'net_revenue_idr', 'active_subscribers_starter', 'active_subscribers_pro', 
      'active_subscribers_elite', 'active_subscribers_ultimate', 'wins', 'issues', 'actions'
    ];
    
    // Add custom columns to headers
    customColumns.forEach(c => headers.push(c.key));

    const row = headers.map(h => {
        const val = report[h] || 0;
        return typeof val === 'string' ? `"${val.replace(/"/g, '""')}"` : val;
    }).join(',');

    const csvContent = "data:text/csv;charset=utf-8," + headers.join(',') + "\n" + row;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Tokcer_${report.report_period}_Report_${report.date_end}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportProReport = async (report) => {
    if (!report) return;
    setIsGeneratingPro(true);
    try {
      const prompt = `Anda adalah Udin, Senior Strategic & Financial Analyst untuk Tokcer AI. 
      Buatlah laporan bisnis profesional mendalam untuk Investor dalam format MARKDOWN (.md) berdasarkan data berikut:
      - Gross: IDR ${report.gross_income_idr.toLocaleString()}
      - MRR: IDR ${report.total_mrr_idr.toLocaleString()}
      - User Aktif: ${report.total_active_paid}
      
      Laporan HARUS mencakup 10 poin utama:
      1. Ringkasan Eksekutif, 2. Kinerja Keuangan, 3. Metrik Operasional, 4. Pengguna, 5. Produk, 6. Tim, 7. Pemasaran, 8. Pasar & Risiko, 9. Penggunaan Dana, 10. Milestone.
      
      Tulis dengan gaya bahasa profesional dan tajam. Jangan gunakan JSON, langsung tulis MARKDOWN.`;

      const { text: aiResult } = await callAiEngine("You are Udin, Strategic Growth Lead.", prompt, 8192, 0.5);

      // Save to active report for display
      const updatedReport = { ...report, full_md: aiResult };
      setActiveReport(updatedReport);

      // Export as .md file
      const blob = new Blob([aiResult], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Tokcer_Investor_Report_${report.date_end}.md`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      setIsGeneratingPro(false);
      alert("✅ Laporan Investor (.md) berhasil diunduh!");
    } catch (err) {
      console.error("MD Export Error:", err);
      alert("Gagal membuat laporan .md: " + err.message);
      setIsGeneratingPro(false);
    }
  };

  const filteredReports = reports.filter(r => (r.report_period || 'weekly') === reportPeriod);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tighter uppercase">Business Insight & Analytics</h2>
          <p className="text-xs text-zinc-500 font-bold uppercase tracking-widest mt-1">AI-Powered Financial Reporting System</p>
        </div>
        <div className="flex bg-zinc-900 border border-zinc-800 rounded-xl p-1">
          <button 
            onClick={() => setReportPeriod('weekly')}
            className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${reportPeriod === 'weekly' ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            Weekly
          </button>
          <button 
            onClick={() => setReportPeriod('monthly')}
            className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${reportPeriod === 'monthly' ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'text-zinc-500 hover:text-zinc-300'}`}
          >
            Monthly
          </button>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2">
             <label className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all cursor-pointer ${partnerCSV ? 'bg-emerald-600/10 border-emerald-500 text-emerald-500' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:bg-zinc-700'}`}>
                <iconify-icon icon={partnerCSV ? "solar:check-circle-bold-duotone" : "solar:file-send-bold-duotone"} className="text-base"></iconify-icon>
                Partner Report
                <input type="file" accept=".csv" className="hidden" onChange={(e) => handleFileUpload(e, 'partner')} />
             </label>
             <label className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all cursor-pointer ${userNeedsCSV ? 'bg-emerald-600/10 border-emerald-500 text-emerald-500' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:bg-zinc-700'}`}>
                <iconify-icon icon={userNeedsCSV ? "solar:check-circle-bold-duotone" : "solar:user-speak-bold-duotone"} className="text-base"></iconify-icon>
                User Report
                <input type="file" accept=".csv" className="hidden" onChange={(e) => handleFileUpload(e, 'user')} />
             </label>
          </div>
          <button 
            onClick={handleGenerateReport}
            disabled={isGenerating || isUploading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-600/20 transition-all"
          >
            {isGenerating ? (
              <iconify-icon icon="solar:spinner-linear" className="animate-spin text-lg"></iconify-icon>
            ) : (
              <iconify-icon icon="solar:magic-stick-bold-duotone" className="text-lg"></iconify-icon>
            )}
            Generate {reportPeriod === 'weekly' ? 'Weekly' : 'Monthly'} Report
          </button>
        </div>
      </header>

      {/* Overview Cards */}
      {activeReport && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Gross Income', val: `IDR ${activeReport.gross_income_idr.toLocaleString()}`, icon: 'solar:wallet-money-bold-duotone', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
            { label: 'Total MRR', val: `IDR ${activeReport.total_mrr_idr.toLocaleString()}`, icon: 'solar:refresh-bold-duotone', color: 'text-blue-400', bg: 'bg-blue-500/10' },
            { label: 'Active Paid Users', val: activeReport.total_active_paid, icon: 'solar:users-group-rounded-bold-duotone', color: 'text-amber-400', bg: 'bg-amber-500/10' },
            { label: 'Net Revenue', val: `IDR ${activeReport.net_revenue_idr.toLocaleString()}`, icon: 'solar:hand-stars-bold-duotone', color: 'text-purple-400', bg: 'bg-purple-500/10' },
          ].map((stat, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 p-5 rounded-2xl shadow-sm hover:border-zinc-700 transition-all group">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center`}>
                  <iconify-icon icon={stat.icon} className={`text-xl ${stat.color}`}></iconify-icon>
                </div>
                <div className="text-[10px] font-black text-zinc-600 group-hover:text-zinc-400">REALTIME</div>
              </div>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{stat.label}</p>
              <h3 className="text-xl font-black text-white mt-1 tracking-tighter">{stat.val}</h3>
            </div>
          ))}
        </div>
      )}

      {/* AI Analysis View */}
      {activeReport && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="bg-zinc-900/50 p-4 border-b border-zinc-800 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <iconify-icon icon="solar:notes-bold-duotone" className="text-blue-500 text-xl"></iconify-icon>
                  <span className="text-[10px] font-black text-white uppercase tracking-widest">AI Business Summary</span>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => exportToCSV(activeReport)}
                    className="text-[10px] font-black text-zinc-500 hover:text-white flex items-center gap-1 uppercase tracking-widest px-3 py-1.5 border border-zinc-800 rounded-lg"
                  >
                    <iconify-icon icon="solar:file-text-bold-duotone" className="text-base"></iconify-icon>
                    CSV
                  </button>
                  <button 
                    onClick={() => handleExportProReport(activeReport)}
                    disabled={isGeneratingPro}
                    className="text-[10px] font-black text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-1 uppercase tracking-widest px-4 py-1.5 rounded-lg shadow-lg shadow-blue-600/20 disabled:opacity-50"
                  >
                    {isGeneratingPro ? (
                      <iconify-icon icon="solar:spinner-linear" className="animate-spin text-base"></iconify-icon>
                    ) : (
                      <iconify-icon icon="solar:crown-bold-duotone" className="text-base text-amber-300"></iconify-icon>
                    )}
                    Export Pro Report (.md)
                  </button>
                </div>
              </div>
              
              <div className="p-8 space-y-8">
                {activeReport.full_md ? (
                   <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl p-6">
                      <div className="prose prose-invert max-w-none">
                         <div className="whitespace-pre-wrap text-sm text-zinc-300 leading-relaxed font-mono">
                            {activeReport.full_md}
                         </div>
                      </div>
                   </div>
                ) : (
                  <>
                    {[
                      { id: 'fh', title: 'Part 1: Financial Health', data: activeReport.executive_summary?.financial_health, icon: 'solar:wallet-money-bold-duotone', color: 'text-emerald-500', bg: 'bg-emerald-500/5' },
                      { id: 'sm', title: 'Part 2: Subscriber Movement', data: activeReport.executive_summary?.subscriber_movement, icon: 'solar:users-group-rounded-bold-duotone', color: 'text-blue-500', bg: 'bg-blue-500/5' },
                      { id: 'pp', title: 'Part 3: Partner Performance', data: activeReport.executive_summary?.partner_performance, icon: 'solar:hand-stars-bold-duotone', color: 'text-purple-500', bg: 'bg-purple-500/5' },
                      { id: 'of', title: 'Part 4: Organic Funnel', data: activeReport.executive_summary?.organic_funnel, icon: 'solar:graph-bold-duotone', color: 'text-amber-500', bg: 'bg-amber-500/5' },
                      { id: 'ra', title: 'Part 5: Risk & Alert 🚨', data: activeReport.executive_summary?.risk_alert, icon: 'solar:danger-bold-duotone', color: 'text-rose-500', bg: 'bg-rose-500/5' },
                      { id: 'sr', title: 'Part 6: Strategic Recommendation', data: activeReport.executive_summary?.strategic_recommendation, icon: 'solar:magic-stick-bold-duotone', color: 'text-indigo-500', bg: 'bg-indigo-500/5' },
                    ].map((section) => (
                      <div key={section.id} className="animate-in fade-in slide-in-from-left-4 duration-500">
                        <h4 className={`text-[10px] font-black ${section.color} uppercase tracking-widest mb-3 flex items-center gap-2`}>
                          <iconify-icon icon={section.icon}></iconify-icon>
                          {section.title}
                        </h4>
                        <div className={`p-4 ${section.bg} border border-white/5 rounded-xl`}>
                          <ul className="space-y-2">
                            {Array.isArray(section.data) ? section.data.map((point, idx) => (
                              <li key={idx} className="flex gap-3 text-xs text-zinc-300 leading-relaxed">
                                <span className="text-zinc-600 mt-1">•</span>
                                {point}
                              </li>
                            )) : <li className="text-xs text-zinc-500 italic">No data available</li>}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </>
                )}
                
                <div className="pt-6 border-t border-zinc-800">
                   <div className="flex justify-between items-center mb-3">
                      <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Progress to 100M Target</span>
                      <span className="text-[10px] font-black text-white uppercase tracking-widest">{activeReport.progress_target}%</span>
                   </div>
                   <div className="w-full bg-zinc-900 rounded-full h-2.5 overflow-hidden border border-zinc-800">
                      <div 
                        className="bg-gradient-to-r from-blue-600 to-indigo-400 h-full transition-all duration-1000" 
                        style={{ width: `${Math.min(activeReport.progress_target, 100)}%` }}
                      ></div>
                   </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-[10px] font-black text-white uppercase tracking-widest mb-6 flex items-center gap-2">
                <iconify-icon icon="solar:history-bold-duotone" className="text-zinc-500"></iconify-icon>
                {reportPeriod === 'weekly' ? 'Weekly' : 'Monthly'} History
              </h3>
              <div className="space-y-3">
                {filteredReports.map((r, i) => (
                  <div 
                    key={i} 
                    className={`flex items-center justify-between p-4 border rounded-2xl transition-all cursor-pointer group ${activeReport?.id === r.id ? 'bg-blue-600/10 border-blue-500' : 'bg-black border-zinc-800 hover:border-zinc-700'}`} 
                    onClick={() => {
                        setActiveReport(r);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-[10px] font-black transition-all ${activeReport?.id === r.id ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-500 group-hover:bg-blue-600 group-hover:text-white'}`}>
                        {r.report_week}
                      </div>
                      <div>
                        <p className="text-[10px] font-black text-white uppercase">{r.date_end}</p>
                        <p className="text-[8px] font-bold text-zinc-600 uppercase tracking-widest">Financial Report</p>
                      </div>
                    </div>
                    <iconify-icon icon="solar:alt-arrow-right-linear" className={`transition-all ${activeReport?.id === r.id ? 'text-blue-500 rotate-90' : 'text-zinc-700 group-hover:text-white'}`}></iconify-icon>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {!activeReport && (
        <div className="flex flex-col items-center justify-center py-20 bg-zinc-950 border border-zinc-800 rounded-3xl border-dashed">
          <div className="w-20 h-20 rounded-full bg-zinc-900 flex items-center justify-center mb-6">
            <iconify-icon icon="solar:graph-bold-duotone" className="text-4xl text-zinc-700"></iconify-icon>
          </div>
          <h3 className="text-xl font-black text-white uppercase tracking-tighter">Belum ada laporan aktif</h3>
          <p className="text-xs text-zinc-600 font-bold uppercase tracking-widest mt-2">Klik tombol generate untuk memulai analisa minggu ini</p>
        </div>
      )}

      {/* Add Column Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-3xl p-8 shadow-2xl animate-in zoom-in-95 duration-300">
            <h3 className="text-lg font-black text-white uppercase tracking-tighter mb-6 flex items-center gap-2">
              <iconify-icon icon="solar:add-circle-bold-duotone" className="text-blue-500"></iconify-icon>
              Add Custom Column
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1 mb-2 block">Column Name (Label)</label>
                <input 
                  type="text" 
                  value={newColumn.name}
                  onChange={(e) => setNewColumn({...newColumn, name: e.target.value})}
                  placeholder="e.g. Operating Cost"
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>
              <div>
                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1 mb-2 block">Field Key (CSV Key)</label>
                <input 
                  type="text" 
                  value={newColumn.key}
                  onChange={(e) => setNewColumn({...newColumn, key: e.target.value})}
                  placeholder="e.g. op_cost_idr"
                  className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition-all"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-8">
              <button onClick={() => setIsModalOpen(false)} className="flex-1 py-3 bg-zinc-800 text-zinc-400 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-zinc-700 transition-all">Cancel</button>
              <button onClick={handleAddColumn} className="flex-1 py-3 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-all">Add Column</button>
            </div>
          </div>
        </div>
      )}
      {/* HIDDEN PDF TEMPLATE */}
      {proReportHtml && (
        <div id={`pro-report-temp-${proReportHtml.id}`} className="fixed left-[-9999px] top-0 w-[800px] bg-black p-12 text-white font-['Inter',sans-serif]">
          <div className="border-b-4 border-blue-600 pb-8 mb-10 flex justify-between items-end">
            <div>
              <h1 className="text-4xl font-black uppercase tracking-tighter text-white">Investor Report</h1>
              <p className="text-blue-500 font-bold uppercase tracking-[0.3em] text-xs mt-2">Tokcer AI Business Intelligence</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] font-black text-zinc-500 uppercase">Periode Laporan</p>
              <p className="text-sm font-bold text-white">{proReportHtml.date_start} s/d {proReportHtml.date_end}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 mb-12">
            <div className="bg-zinc-900/50 p-6 rounded-3xl border border-zinc-800">
               <div className="flex items-center gap-2 mb-4">
                  <iconify-icon icon="solar:chart-square-bold-duotone" className="text-emerald-500"></iconify-icon>
                  <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Revenue Growth (Visual)</p>
               </div>
               <div className="flex items-end gap-2 h-24 mb-2">
                  {[40, 70, 45, 90, 65, 85, 100].map((h, i) => (
                    <div key={i} className="flex-1 bg-emerald-500/20 border-t-2 border-emerald-500 rounded-t-sm" style={{ height: `${h}%` }}></div>
                  ))}
               </div>
               <p className="text-3xl font-black text-emerald-400">IDR {proReportHtml.gross_income_idr.toLocaleString()}</p>
            </div>
            <div className="bg-zinc-900/50 p-6 rounded-3xl border border-zinc-800">
               <div className="flex items-center gap-2 mb-4">
                  <iconify-icon icon="solar:user-plus-bold-duotone" className="text-blue-500"></iconify-icon>
                  <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">User Adoption (Trend)</p>
               </div>
               <div className="relative h-24 mb-2 flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 100 40">
                    <path d="M0 35 Q 25 30, 50 15 T 100 5" fill="none" stroke="#3b82f6" strokeWidth="2" />
                    <circle cx="100" cy="5" r="2" fill="#3b82f6" />
                  </svg>
               </div>
               <p className="text-3xl font-black text-blue-400">{proReportHtml.progress_target}% to Target</p>
            </div>
          </div>

          <div className="space-y-10">
            {[1,2,3,4,5,6,7,8,9,10].map(num => (
              <div key={num} className="page-break-inside-avoid">
                <div className="flex items-center gap-3 mb-4">
                   <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-xs font-black text-white">{num}</div>
                   <h2 className="text-lg font-black uppercase tracking-tight text-white border-b border-zinc-800 flex-1 pb-1">
                     {num === 1 && "Ringkasan Eksekutif"}
                     {num === 2 && "Kinerja Keuangan"}
                     {num === 3 && "Metrik Operasional & Pertumbuhan"}
                     {num === 4 && "Pengguna & Pelanggan"}
                     {num === 5 && "Produk & Pengembangan"}
                     {num === 6 && "Tim & SDM"}
                     {num === 7 && "Pemasaran & Penjualan"}
                     {num === 8 && "Pasar, Kompetisi & Risiko"}
                     {num === 9 && "Penggunaan Dana"}
                     {num === 10 && "Milestone & Rencana Mendatang"}
                   </h2>
                </div>
                <div className="pl-11 pr-4">
                  <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                    {proReportHtml.narrative[`section${num}`] || "Menganalisis data..."}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-20 pt-10 border-t border-zinc-800 text-center">
            <p className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.5em]">Confidential - Generated by Tokcer AI Core</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BusinessInsightSection;
