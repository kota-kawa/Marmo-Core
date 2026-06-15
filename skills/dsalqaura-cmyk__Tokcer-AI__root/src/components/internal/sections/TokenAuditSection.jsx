import React, { useState, useEffect } from 'react';
import { supabase } from '../../../lib/supabase.js';

const TokenAuditSection = ({ t }) => {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({
    totalInput: 0,
    totalOutput: 0,
    totalTokens: 0,
    totalCostUSD: 0,
    topFeature: '-',
    totalCalls: 0
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setIsLoading(true);
    try {
      // 🏮 RESILIENT FETCH: Mengambil log secara mandiri untuk menghindari error JOIN
      const { data, error } = await supabase
        .from('ai_usage_logs')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;

      // Jika data ada, coba ambil profil pendukung (secara opsional)
      const logsWithProfiles = data || [];
      
      setLogs(logsWithProfiles);
      calculateStats(logsWithProfiles);
    } catch (err) {
      console.error("Error fetching AI logs:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const calculateStats = (data) => {
    let input = 0;
    let output = 0;
    let total = 0;
    let costUSD = 0;

    data.forEach(log => {
      const i = log.input_tokens || 0;
      const o = log.output_tokens || 0;
      const t = log.tokens_used || (i + o) || 0;
      
      input += i;
      output += o;
      total += t;

      // DeepSeek Pricing: Input $0.14/1M, Output $0.28/1M
      costUSD += (i / 1000000 * 0.14) + (o / 1000000 * 0.28);
      if (i === 0 && o === 0 && t > 0) {
        costUSD += (t / 1000000 * 0.20);
      }
    });

    const features = data.reduce((acc, curr) => {
      const f = curr.feature || 'unknown';
      acc[f] = (acc[f] || 0) + (curr.input_tokens + curr.output_tokens || curr.tokens_used || 0);
      return acc;
    }, {});

    const topF = Object.entries(features).sort((a, b) => b[1] - a[1])[0]?.[0] || '-';

    setStats({
      totalInput: input,
      totalOutput: output,
      totalTokens: total,
      totalCostUSD: costUSD,
      topFeature: topF,
      totalCalls: data.length
    });
  };

  const formatIDR = (usd) => {
    const USD_IDR_RATE = 17300; // Selaraskan dengan kurs default di AccountingSection
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 2
    }).format(usd * USD_IDR_RATE);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">
      {/* Financial Summary */}
      <div className="bg-gradient-to-br from-zinc-900 to-black border border-zinc-800 p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <iconify-icon icon="solar:calculator-minimalistic-bold-duotone" className="text-9xl text-white"></iconify-icon>
        </div>
        <div className="relative z-10">
          <p className="text-zinc-500 text-xs font-black uppercase tracking-[0.2em] mb-4">Total Estimated Expenditure</p>
          <div className="flex flex-col md:flex-row md:items-end gap-2 md:gap-6">
            <h1 className="text-5xl font-black text-white tracking-tighter">{formatIDR(stats.totalCostUSD)}</h1>
            <p className="text-emerald-500 font-bold mb-2 text-sm">~ ${stats.totalCostUSD.toFixed(4)} USD</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-8 border-t border-zinc-800/50 pt-8">
            <div>
              <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest mb-1">Total Tokens</p>
              <p className="text-xl font-bold text-white">{stats.totalTokens.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest mb-1">Input (0.14/1M)</p>
              <p className="text-xl font-bold text-zinc-400">{stats.totalInput.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest mb-1">Output (0.28/1M)</p>
              <p className="text-xl font-bold text-zinc-400">{stats.totalOutput.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-zinc-600 text-[10px] font-black uppercase tracking-widest mb-1">API Requests</p>
              <p className="text-xl font-bold text-orange-500">{stats.totalCalls.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-zinc-900/30 border border-zinc-800 rounded-3xl p-6">
          <h3 className="text-sm font-black text-white uppercase tracking-widest mb-6">Usage by Menu</h3>
          <div className="space-y-4">
            {Object.entries(
                logs.reduce((acc, curr) => {
                    const f = curr.feature || 'unknown';
                    acc[f] = (acc[f] || 0) + (curr.input_tokens + curr.output_tokens || curr.tokens_used || 0);
                    return acc;
                }, {})
            ).sort((a,b) => b[1] - a[1]).map(([feature, tokens]) => (
                <div key={feature} className="group">
                    <div className="flex justify-between text-[10px] font-bold uppercase mb-1.5">
                        <span className="text-zinc-400 group-hover:text-white transition-colors">{feature.replace(/_/g, ' ')}</span>
                        <span className="text-zinc-500">{stats.totalTokens > 0 ? ((tokens / stats.totalTokens) * 100).toFixed(1) : 0}%</span>
                    </div>
                    <div className="h-1.5 bg-black rounded-full overflow-hidden border border-zinc-800/50">
                        <div 
                            className="h-full bg-orange-500 shadow-[0_0_10px_rgba(249,115,22,0.5)] rounded-full transition-all duration-1000" 
                            style={{ width: `${stats.totalTokens > 0 ? (tokens / stats.totalTokens) * 100 : 0}%` }}
                        ></div>
                    </div>
                    <p className="text-[9px] text-zinc-600 mt-1 font-mono">{tokens.toLocaleString()} tokens</p>
                </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 bg-zinc-900/30 border border-zinc-800 rounded-3xl overflow-hidden">
          <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
            <h3 className="text-sm font-black text-white uppercase tracking-widest">Audit Trail</h3>
            <button onClick={fetchLogs} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white transition-all">
                <iconify-icon icon="solar:restart-bold-duotone" className={isLoading ? 'animate-spin' : ''}></iconify-icon>
            </button>
          </div>
          <div className="overflow-x-auto max-h-[400px] custom-scrollbar">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-zinc-900 z-10 border-b border-zinc-800">
                <tr className="text-zinc-600 text-[9px] font-black uppercase tracking-widest">
                  <th className="px-6 py-4">Feature & Details</th>
                  <th className="px-6 py-4 text-right">Tokens (I/O)</th>
                  <th className="px-6 py-4 text-right">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/30">
                {logs.map((log) => {
                  const logCost = ((log.input_tokens || 0) / 1000000 * 0.14) + ((log.output_tokens || 0) / 1000000 * 0.28);
                  return (
                    <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4">
                        <p className="text-[10px] text-zinc-500 uppercase font-black tracking-tighter mb-0.5">{log.feature?.replace(/_/g, ' ')}</p>
                        <p className="text-[9px] text-zinc-600 truncate w-48">{log.prompt?.substring(0, 50)}...</p>
                      </td>
                      <td className="px-6 py-4 text-right font-mono">
                        <p className="text-xs text-white">{((log.input_tokens || 0) + (log.output_tokens || 0) || log.tokens_used || 0).toLocaleString()}</p>
                        <p className="text-[9px] text-zinc-600">{(log.input_tokens || 0).toLocaleString()} / {(log.output_tokens || 0).toLocaleString()}</p>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-emerald-500 font-bold text-[11px]">{formatIDR(logCost || (log.tokens_used / 1000000 * 0.20))}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TokenAuditSection;
