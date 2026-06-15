import React from 'react';

const SupabaseSection = ({ t }) => {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
       <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'DB Connections', value: '42/100', color: 'text-green-500', trend: 'Healthy' },
          { label: 'Storage Used', value: '1.2GB/5GB', color: 'text-amber-500', trend: '24% Full' },
          { label: 'Avg API Latency', value: '45ms', color: 'text-blue-500', trend: 'Optimized' },
          { label: 'Active Sessions', value: '1,256', color: 'text-purple-500', trend: 'Live' }
        ].map(s => (
          <div key={s.label} className="bg-zinc-900/50 p-6 rounded-[2rem] border border-zinc-800 text-center relative overflow-hidden group">
            <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-3">{s.label}</p>
            <p className={`text-3xl font-black ${s.color} tracking-tighter`}>{s.value}</p>
            <p className="text-[8px] font-black text-zinc-600 uppercase mt-4 tracking-widest">{s.trend}</p>
          </div>
        ))}
      </div>
      <div className="bg-zinc-900/50 p-12 rounded-[3rem] border border-zinc-800 text-center relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl"></div>
        <iconify-icon icon="solar:settings-bold-duotone" className="text-6xl text-zinc-800 mb-6 animate-spin-slow"></iconify-icon>
        <h3 className="text-xl font-black text-white uppercase tracking-tight">{t('infraHub')}</h3>
        <p className="text-zinc-500 text-sm mt-2 max-w-lg mx-auto uppercase font-bold tracking-[0.1em]">Connected to project `iogxyo...`. Monitoring real-time data flow, authentication triggers, and storage bucket accessibility.</p>
        
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {['Auth Service', 'PostgREST', 'Realtime', 'Storage'].map(srv => (
                <div key={srv} className="flex items-center gap-2 justify-center py-2 px-4 rounded-full bg-zinc-950 border border-zinc-800">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                    <span className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">{srv === 'Auth Service' ? t('authService') : srv} OK</span>
                </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default SupabaseSection;
