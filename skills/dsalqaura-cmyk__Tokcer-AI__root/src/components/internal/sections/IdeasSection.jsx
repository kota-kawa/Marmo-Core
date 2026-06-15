import React from 'react';
import { supabase } from '../../../lib/supabase.js';

const IdeasSection = ({ 
  t, 
  ideas,
  fetchIdeas
}) => {
  const handleStatusUpdate = async (id, newStatus) => {
    try {
      const { error } = await supabase
        .from('partner_ideas')
        .update({ status: newStatus })
        .eq('id', id);
      
      if (error) throw error;
      if (fetchIdeas) fetchIdeas();
    } catch (err) {
      alert("Error updating idea: " + err.message);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
       <div className="bg-zinc-900/50 rounded-3xl border border-zinc-800 p-6 md:p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="font-black text-white uppercase tracking-tight text-xl">Saran Fitur Partner</h3>
              <p className="text-xs text-zinc-500 mt-1 uppercase tracking-widest font-bold">Ide Brilian dari Para Partner</p>
            </div>
            <div className="bg-zinc-950 px-4 py-2 rounded-xl border border-zinc-800 flex items-center gap-3">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">{ideas.filter(i => i.status === 'draft' || i.status === 'open').length} Baru</span>
            </div>
          </div>

          <div className="space-y-4">
            {ideas.length > 0 ? ideas.map(item => (
              <div key={item.id} className="bg-zinc-950 p-6 rounded-2xl border border-zinc-800 group hover:border-zinc-600 transition-all">
                 <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                    <div className="flex gap-5 items-start">
                       <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 bg-blue-500/10 text-blue-400">
                          <iconify-icon icon="solar:lightbulb-bold-duotone" className="text-2xl"></iconify-icon>
                       </div>
                       <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-black text-white uppercase tracking-tight">{item.title || 'Saran Fitur'}</h4>
                            <span className={`text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-widest ${
                              item.status === 'draft' || item.status === 'open' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'
                            }`}>
                              {item.status}
                            </span>
                          </div>
                          <p className="text-xs text-zinc-400 leading-relaxed mb-3 max-w-2xl">{item.content}</p>
                          <div className="flex items-center gap-4">
                            <p className="text-[10px] text-zinc-500 font-bold uppercase">
                              BY: <span className="text-zinc-300">{item.partners?.full_name || 'System'}</span> 
                            </p>
                          </div>
                       </div>
                    </div>
                    <div className="flex items-center gap-2 w-full lg:w-auto">
                       {item.status === 'draft' || item.status === 'open' ? (
                         <>
                           <button 
                            onClick={() => handleStatusUpdate(item.id, 'reviewed')}
                            className="flex-1 lg:flex-none px-5 py-2.5 bg-emerald-600 text-white text-[9px] font-black uppercase tracking-widest rounded-xl hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/10"
                           >
                            TANDAI DIREVIEW
                           </button>
                           <button 
                            onClick={() => handleStatusUpdate(item.id, 'rejected')}
                            className="flex-1 lg:flex-none px-5 py-2.5 bg-zinc-800 text-zinc-500 text-[9px] font-black uppercase tracking-widest rounded-xl hover:bg-rose-600 hover:text-white transition-all border border-zinc-700"
                           >
                            ABAIKAN
                           </button>
                         </>
                       ) : (
                         <div className="text-[9px] font-black text-zinc-600 uppercase tracking-[0.2em] px-4 py-2 bg-zinc-900 rounded-xl border border-zinc-800">
                            PROCESSED
                         </div>
                       )}
                    </div>
                 </div>
              </div>
            )) : (
              <div className="py-20 flex flex-col items-center justify-center text-center">
                <iconify-icon icon="solar:tea-cup-linear" className="text-5xl text-zinc-800 mb-4"></iconify-icon>
                <p className="text-zinc-600 text-sm font-medium tracking-wide uppercase">Belum ada saran fitur baru dari Partner.</p>
              </div>
            )}
          </div>
       </div>
    </div>
  );
};

export default IdeasSection;
