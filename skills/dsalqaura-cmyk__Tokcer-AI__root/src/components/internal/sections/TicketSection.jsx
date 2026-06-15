import React, { useState } from 'react';
import { supabase } from '../../../lib/supabase.js';

const TicketSection = ({ 
  t, 
  tickets,
  fetchTickets
}) => {
  const [previewImage, setPreviewImage] = useState(null);
  const handleStatusUpdate = async (id, newStatus) => {
    try {
      const { error } = await supabase
        .from('support_tickets')
        .update({ status: newStatus })
        .eq('id', id);
      
      if (error) throw error;
      if (fetchTickets) fetchTickets();
    } catch (err) {
      alert("Error updating ticket: " + err.message);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
       <div className="bg-zinc-900/50 rounded-3xl border border-zinc-800 p-6 md:p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="font-black text-white uppercase tracking-tight text-xl">{t('feedbackLoop')}</h3>
              <p className="text-xs text-zinc-500 mt-1 uppercase tracking-widest font-bold">User & Partner Support Center</p>
            </div>
            <div className="bg-zinc-950 px-4 py-2 rounded-xl border border-zinc-800 flex items-center gap-3">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">{tickets.filter(t => t.status === 'open').length} {t('active')}</span>
            </div>
          </div>

          <div className="space-y-4">
            {tickets.length > 0 ? tickets.map(t_item => (
              <div key={t_item.id} className="bg-zinc-950 p-6 rounded-2xl border border-zinc-800 group hover:border-zinc-600 transition-all">
                 <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                    <div className="flex gap-5 items-start">
                       <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${
                         t_item.type === 'bug' ? 'bg-rose-500/10 text-rose-500' : 'bg-blue-500/10 text-blue-400'
                       }`}>
                          <iconify-icon icon={t_item.type === 'bug' ? "solar:shield-warning-bold-duotone" : "solar:magic-stick-3-bold-duotone"} className="text-2xl"></iconify-icon>
                       </div>
                       <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-black text-white uppercase tracking-tight">{t_item.title || t_item.category}</h4>
                            <span className={`text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-widest ${
                              t_item.status === 'open' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'
                            }`}>
                              {t_item.status}
                            </span>
                          </div>
                          <p className="text-xs text-zinc-400 leading-relaxed mb-3 max-w-2xl">{t_item.description}</p>
                          <div className="flex items-center gap-4">
                            <p className="text-[10px] text-zinc-500 font-bold uppercase">
                              BY: <span className="text-zinc-300">{t_item.partners?.full_name || t_item.clients?.shop_name || 'System'}</span> 
                              <span className="mx-2 text-zinc-800">|</span> 
                              {t_item.type?.toUpperCase()}
                            </p>
                            {t_item.attachment_url && (
                              <button 
                                onClick={() => setPreviewImage(t_item.attachment_url)}
                                className="flex items-center gap-1.5 text-[9px] font-black text-orange-500 uppercase tracking-widest hover:text-orange-400 transition-all bg-orange-500/5 px-2.5 py-1.5 rounded-lg border border-orange-500/10"
                              >
                                <iconify-icon icon="solar:paperclip-linear"></iconify-icon>
                                VIEW SCREENSHOT
                              </button>
                            )}
                          </div>
                       </div>
                    </div>
                    <div className="flex items-center gap-2 w-full lg:w-auto">
                       {t_item.status === 'open' ? (
                         <>
                           <button 
                            onClick={() => handleStatusUpdate(t_item.id, 'resolved')}
                            className="flex-1 lg:flex-none px-5 py-2.5 bg-emerald-600 text-white text-[9px] font-black uppercase tracking-widest rounded-xl hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/10"
                           >
                            {t('resolve') || 'RESOLVE'}
                           </button>
                           <button 
                            onClick={() => handleStatusUpdate(t_item.id, 'closed')}
                            className="flex-1 lg:flex-none px-5 py-2.5 bg-zinc-800 text-zinc-500 text-[9px] font-black uppercase tracking-widest rounded-xl hover:bg-rose-600 hover:text-white transition-all border border-zinc-700"
                           >
                            {t('reject') || 'CLOSE'}
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
                <p className="text-zinc-600 text-sm font-medium tracking-wide uppercase">All quiet on the support front. Nice job!</p>
              </div>
            )}
          </div>
       </div>

      {/* Screenshot Preview Modal (Glassmorphism & Secure) */}
      {previewImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-300"
          onClick={() => setPreviewImage(null)}
        >
          <div 
            className="relative max-w-4xl w-full bg-zinc-950/90 rounded-3xl border border-zinc-800 p-4 overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex justify-between items-center pb-3 border-b border-zinc-900/80 mb-3">
              <div className="flex items-center gap-2">
                <iconify-icon icon="solar:image-line" className="text-orange-500 text-lg"></iconify-icon>
                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Attachment Screenshot Preview</span>
              </div>
              <button 
                onClick={() => setPreviewImage(null)}
                className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
              >
                <iconify-icon icon="solar:close-circle-bold" className="text-lg"></iconify-icon>
              </button>
            </div>
            
            {/* High Res Image Container */}
            <div className="flex justify-center items-center bg-black/60 rounded-2xl p-1 overflow-auto max-h-[75vh]">
              <img 
                src={previewImage} 
                alt="Screenshot Preview" 
                className="max-w-full max-h-[72vh] object-contain rounded-xl select-none"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketSection;
