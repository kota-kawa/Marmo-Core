import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../../lib/supabase.js';

const STATUS_COLORS = {
  pending:    'bg-amber-500/10 text-amber-400 border-amber-500/20',
  processing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  posted:     'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  failed:     'bg-red-500/10 text-red-400 border-red-500/20',
  downloaded: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
};

const isStorageUrl = (path) => path && (path.startsWith('http://') || path.startsWith('https://'));
const isLocalPath  = (path) => path && !isStorageUrl(path);

const formatDate = (d) => d
  ? new Date(d).toLocaleString('id-ID', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' })
  : '-';

const TikTokQueueSection = ({ t }) => {
  const [activeTab,     setActiveTab]     = useState('queue');
  const [queue,         setQueue]         = useState([]);
  const [history,       setHistory]       = useState([]);
  const [isLoading,     setIsLoading]     = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const [deletingId,    setDeletingId]    = useState(null);
  const [filterStatus,  setFilterStatus]  = useState('all');
  const [copiedId,      setCopiedId]      = useState(null);
  const [stats,         setStats]         = useState({ pending:0, downloaded:0, posted:0, failed:0 });

  // ── Fetch queue ────────────────────────────────────────────────────────────
  const fetchQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      let q = supabase.from('upload_queue').select('*').order('scheduled_time', { ascending: false }).limit(50);
      if (filterStatus !== 'all') q = q.eq('status', filterStatus);
      const { data, error } = await q;
      if (error) throw error;
      setQueue(data || []);

      const { data: all } = await supabase.from('upload_queue').select('status');
      if (all) {
        const c = { pending:0, downloaded:0, posted:0, failed:0 };
        all.forEach(r => { if (c[r.status] !== undefined) c[r.status]++; });
        setStats(c);
      }
    } catch (err) { console.error('[Queue] fetch error:', err); }
    finally { setIsLoading(false); }
  }, [filterStatus]);

  // ── Fetch history ──────────────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    const { data, error } = await supabase
      .from('tiktok_download_history')
      .select('*')
      .order('downloaded_at', { ascending: false })
      .limit(100);
    if (!error) setHistory(data || []);
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);
  useEffect(() => { if (activeTab === 'history') fetchHistory(); }, [activeTab, fetchHistory]);

  // ── Copy caption ───────────────────────────────────────────────────────────
  const handleCopyCaption = async (text, id) => {
    try { await navigator.clipboard.writeText(text || ''); }
    catch { const el = document.createElement('textarea'); el.value = text||''; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el); }
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // ── Download ───────────────────────────────────────────────────────────────
  const handleDownload = async (job) => {
    if (downloadingId) return;
    const videoPath = job.video_path;

    if (isLocalPath(videoPath)) {
      alert('⚠️ Video belum tersedia.\nPath masih lokal di server bot.\nCaption disalin ke clipboard.');
      await handleCopyCaption(job.caption, job.id);
      return;
    }

    setDownloadingId(job.id);
    try {
      const response = await fetch(videoPath);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob    = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a       = document.createElement('a');
      a.href        = blobUrl;
      a.download    = `tokcer_tiktok_${job.id.slice(0,8)}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);

      // Copy caption otomatis
      await handleCopyCaption(job.caption, job.id);

      // Simpan ke history
      const title = job.caption?.split(' - ')[0] || 'Video TikTok';
      await supabase.from('tiktok_download_history').insert([{
        queue_id:    job.id,
        title,
        caption:     job.caption || '',
        storage_url: videoPath,
        ready_at:    job.scheduled_time || job.created_at,
        downloaded_at: new Date().toISOString(),
        uploaded_to_tiktok: false,
      }]);

      // Update status jadi 'downloaded' — TIDAK dihapus
      await supabase.from('upload_queue').update({ status: 'downloaded' }).eq('id', job.id);
      setQueue(prev => prev.map(j => j.id === job.id ? { ...j, status: 'downloaded' } : j));

      alert('✅ Download berhasil!\nCaption sudah tersalin ke clipboard.\nSilakan upload ke TikTok.');
    } catch (err) {
      console.error('[Download] error:', err);
      alert('❌ Gagal download: ' + err.message + '\nRecord tidak dihapus.');
    } finally {
      setDownloadingId(null);
    }
  };

  // ── Hapus manual dari queue ────────────────────────────────────────────────
  const handleManualDelete = async (job) => {
    if (!window.confirm(`Hapus "${job.caption?.slice(0,50)}..." dari queue?`)) return;
    setDeletingId(job.id);
    try {
      const { error } = await supabase.from('upload_queue').delete().eq('id', job.id);
      if (error) throw error;
      setQueue(prev => prev.filter(j => j.id !== job.id));
    } catch (err) { alert('Gagal hapus: ' + err.message); }
    finally { setDeletingId(null); }
  };

  // ── Mark uploaded to TikTok di history ────────────────────────────────────
  const handleMarkUploaded = async (histId) => {
    const { error } = await supabase
      .from('tiktok_download_history')
      .update({ uploaded_to_tiktok: true, uploaded_at: new Date().toISOString() })
      .eq('id', histId);
    if (!error) setHistory(prev => prev.map(h => h.id === histId ? { ...h, uploaded_to_tiktok: true, uploaded_at: new Date().toISOString() } : h));
  };

  const filteredQueue = filterStatus === 'all' ? queue : queue.filter(j => j.status === filterStatus);
  const localPathCount = queue.filter(j => isLocalPath(j.video_path)).length;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white uppercase tracking-tight flex items-center gap-3">
            <div className="w-10 h-10 bg-zinc-800 rounded-2xl flex items-center justify-center border border-zinc-700">
              <iconify-icon icon="ri:tiktok-fill" className="text-xl text-white"></iconify-icon>
            </div>
            TikTok Video Queue
          </h2>
          <p className="text-sm text-zinc-500 mt-1 ml-[52px]">Download video → upload manual ke TikTok → history tersimpan</p>
        </div>
        <button onClick={() => { fetchQueue(); fetchHistory(); }} disabled={isLoading}
          className="flex items-center gap-2 px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all disabled:opacity-50">
          <iconify-icon icon="solar:refresh-bold" className={`text-base ${isLoading ? 'animate-spin' : ''}`}></iconify-icon>
          Refresh
        </button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-1 w-fit">
        {[
          { id: 'queue',   label: 'Video Queue',      icon: 'solar:video-library-bold-duotone' },
          { id: 'history', label: `History (${history.length})`, icon: 'solar:history-bold-duotone' },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === tab.id ? 'bg-white text-black' : 'text-zinc-500 hover:text-white'}`}>
            <iconify-icon icon={tab.icon} className="text-sm"></iconify-icon>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* TAB: QUEUE                                                            */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'queue' && (<>

        {/* Warning path lokal */}
        {localPathCount > 0 && (
          <div className="bg-amber-500/5 border border-amber-500/30 rounded-2xl p-4 flex items-start gap-3">
            <iconify-icon icon="solar:danger-triangle-bold-duotone" className="text-xl text-amber-400 mt-0.5 shrink-0"></iconify-icon>
            <div>
              <p className="text-xs font-black text-amber-300 uppercase tracking-widest mb-1">{localPathCount} Video Belum Bisa Didownload</p>
              <p className="text-xs text-zinc-400">Path masih lokal di server bot. Bot perlu dijalankan ulang dengan versi terbaru agar video terupload ke Supabase Storage.</p>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label:'Pending',    value:stats.pending,    color:'text-amber-400',  bg:'bg-amber-500/10',  border:'border-amber-500/20',  icon:'solar:clock-circle-bold-duotone' },
            { label:'Downloaded', value:stats.downloaded, color:'text-purple-400', bg:'bg-purple-500/10', border:'border-purple-500/20', icon:'solar:download-minimalistic-bold-duotone' },
            { label:'Posted',     value:stats.posted,     color:'text-emerald-400',bg:'bg-emerald-500/10',border:'border-emerald-500/20',icon:'solar:check-circle-bold-duotone' },
            { label:'Failed',     value:stats.failed,     color:'text-red-400',    bg:'bg-red-500/10',    border:'border-red-500/20',    icon:'solar:close-circle-bold-duotone' },
          ].map(s => (
            <div key={s.label} className={`${s.bg} border ${s.border} rounded-2xl p-4 flex items-center gap-3`}>
              <iconify-icon icon={s.icon} className={`text-2xl ${s.color}`}></iconify-icon>
              <div>
                <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">{s.label}</p>
                <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filter */}
        <div className="flex gap-2 flex-wrap">
          {['all','pending','downloaded','posted','failed'].map(s => (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border ${filterStatus===s ? 'bg-white text-black border-white' : 'bg-zinc-900 text-zinc-500 border-zinc-800 hover:border-zinc-600 hover:text-zinc-300'}`}>
              {s === 'all' ? 'Semua' : s}
            </button>
          ))}
        </div>

        {/* Queue list */}
        <div className="bg-zinc-900/50 rounded-[2rem] border border-zinc-800 overflow-hidden shadow-2xl">
          <div className="p-5 border-b border-zinc-800 bg-zinc-950/50 flex items-center justify-between">
            <h3 className="font-black text-white uppercase tracking-tight text-sm">
              Video Queue <span className="text-zinc-500 font-medium normal-case text-xs ml-1">({filteredQueue.length} video)</span>
            </h3>
            <iconify-icon icon="solar:video-library-bold-duotone" className="text-xl text-zinc-500"></iconify-icon>
          </div>

          {isLoading ? (
            <div className="p-16 flex flex-col items-center gap-3 text-zinc-500">
              <iconify-icon icon="solar:spinner-linear" className="text-4xl animate-spin text-blue-500"></iconify-icon>
              <p className="text-xs font-black uppercase tracking-widest">Memuat...</p>
            </div>
          ) : filteredQueue.length === 0 ? (
            <div className="p-16 flex flex-col items-center gap-3 text-zinc-600">
              <iconify-icon icon="solar:video-frame-bold-duotone" className="text-5xl"></iconify-icon>
              <p className="text-xs font-black uppercase tracking-widest">Queue kosong</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/50">
              {filteredQueue.map(job => {
                const videoReady = isStorageUrl(job.video_path);
                return (
                  <div key={job.id} className="p-5 hover:bg-zinc-800/20 transition-all">
                    <div className="flex flex-col md:flex-row md:items-start gap-4">

                      {/* Thumbnail */}
                      <div className={`w-full md:w-16 h-12 rounded-xl border flex items-center justify-center shrink-0 ${videoReady ? 'bg-zinc-800 border-zinc-700' : 'bg-amber-500/5 border-amber-500/20'}`}>
                        <iconify-icon icon={videoReady ? 'solar:video-frame-bold-duotone' : 'solar:danger-triangle-bold-duotone'} className={`text-xl ${videoReady ? 'text-zinc-600' : 'text-amber-500/50'}`}></iconify-icon>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0 space-y-1.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-lg border ${STATUS_COLORS[job.status] || STATUS_COLORS.pending}`}>{job.status}</span>
                          <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-lg border ${videoReady ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                            {videoReady ? '✓ Siap Download' : '⚠ Path Lokal'}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-300 line-clamp-2">{job.caption || <span className="text-zinc-600 italic">Tidak ada caption</span>}</p>
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-[9px] text-zinc-600">
                            <iconify-icon icon="solar:calendar-bold" className="text-xs mr-1"></iconify-icon>
                            Siap: {formatDate(job.scheduled_time)}
                          </span>
                          <span className="text-[9px] text-zinc-700 font-mono truncate max-w-[200px]">{job.video_path}</span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0 flex-wrap md:flex-nowrap">
                        {/* Copy caption */}
                        <button onClick={() => handleCopyCaption(job.caption, job.id)}
                          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all border ${copiedId===job.id ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:text-white'}`}>
                          <iconify-icon icon={copiedId===job.id ? 'solar:check-circle-bold' : 'solar:copy-bold'} className="text-sm"></iconify-icon>
                          {copiedId===job.id ? 'Copied!' : 'Caption'}
                        </button>

                        {/* Download */}
                        {['pending','failed','downloaded','processing'].includes(job.status) && (
                          <button onClick={() => handleDownload(job)} disabled={downloadingId===job.id || deletingId===job.id}
                            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all active:scale-95 disabled:opacity-50 shadow-lg ${videoReady ? 'bg-white text-black hover:bg-zinc-200' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20'}`}>
                            {downloadingId===job.id ? <><iconify-icon icon="solar:spinner-linear" className="text-sm animate-spin"></iconify-icon>Downloading...</> : videoReady ? <><iconify-icon icon="solar:download-minimalistic-bold" className="text-sm"></iconify-icon>Download</> : <><iconify-icon icon="solar:danger-triangle-bold" className="text-sm"></iconify-icon>Belum Siap</>}
                          </button>
                        )}

                        {/* Delete */}
                        <button onClick={() => handleManualDelete(job)} disabled={deletingId===job.id || downloadingId===job.id}
                          className="flex items-center gap-1.5 px-3 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all hover:bg-red-500/20 active:scale-95 disabled:opacity-50">
                          {deletingId===job.id ? <iconify-icon icon="solar:spinner-linear" className="text-sm animate-spin"></iconify-icon> : <iconify-icon icon="solar:trash-bin-trash-bold" className="text-sm"></iconify-icon>}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Link TikTok Studio */}
        <div className="flex items-center gap-4 pt-2">
          <a href="https://studio.tiktok.com" target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all">
            <iconify-icon icon="ri:tiktok-fill" className="text-base"></iconify-icon>
            Buka TikTok Creator Studio
            <iconify-icon icon="solar:arrow-right-up-bold" className="text-xs"></iconify-icon>
          </a>
          <p className="text-[9px] text-zinc-600 italic">Senin 3x · Selasa-Rabu-Jumat 2x · Kamis-Minggu 1x · Sabtu 3x</p>
        </div>
      </>)}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* TAB: HISTORY                                                          */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'history' && (<>

        <div className="bg-zinc-900/50 rounded-[2rem] border border-zinc-800 overflow-hidden shadow-2xl">
          <div className="p-5 border-b border-zinc-800 bg-zinc-950/50 flex items-center justify-between">
            <div>
              <h3 className="font-black text-white uppercase tracking-tight text-sm">Download History</h3>
              <p className="text-[10px] text-zinc-500 mt-0.5">Semua video yang pernah didownload — caption tersimpan permanen</p>
            </div>
            <button onClick={fetchHistory} className="text-zinc-500 hover:text-white transition-colors">
              <iconify-icon icon="solar:refresh-bold" className="text-xl"></iconify-icon>
            </button>
          </div>

          {history.length === 0 ? (
            <div className="p-16 flex flex-col items-center gap-3 text-zinc-600">
              <iconify-icon icon="solar:history-bold-duotone" className="text-5xl"></iconify-icon>
              <p className="text-xs font-black uppercase tracking-widest">Belum ada history</p>
              <p className="text-[10px] text-zinc-700 text-center max-w-xs">Download video dari tab Queue untuk mulai mencatat history.</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/50">
              {history.map(h => (
                <div key={h.id} className="p-5 hover:bg-zinc-800/20 transition-all">
                  <div className="flex flex-col md:flex-row md:items-start gap-4">

                    {/* Status upload TikTok */}
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 border ${h.uploaded_to_tiktok ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-zinc-800 border-zinc-700'}`}>
                      <iconify-icon icon={h.uploaded_to_tiktok ? 'ri:tiktok-fill' : 'solar:clock-circle-bold-duotone'} className={`text-xl ${h.uploaded_to_tiktok ? 'text-emerald-400' : 'text-zinc-500'}`}></iconify-icon>
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-lg border ${h.uploaded_to_tiktok ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-800 text-zinc-500 border-zinc-700'}`}>
                          {h.uploaded_to_tiktok ? '✓ Sudah Upload TikTok' : 'Belum Upload'}
                        </span>
                        <span className="text-[9px] text-zinc-600">
                          <iconify-icon icon="solar:download-minimalistic-bold" className="text-xs mr-1"></iconify-icon>
                          Download: {formatDate(h.downloaded_at)}
                        </span>
                        {h.ready_at && (
                          <span className="text-[9px] text-zinc-600">
                            <iconify-icon icon="solar:calendar-bold" className="text-xs mr-1"></iconify-icon>
                            Siap: {formatDate(h.ready_at)}
                          </span>
                        )}
                      </div>

                      <p className="text-xs font-bold text-white">{h.title}</p>

                      {/* Caption — full, bisa di-copy */}
                      <div className="bg-zinc-950 rounded-xl border border-zinc-800 p-3 relative group">
                        <p className="text-[10px] text-zinc-400 leading-relaxed whitespace-pre-wrap">{h.caption}</p>
                        <button onClick={() => handleCopyCaption(h.caption, h.id)}
                          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 bg-zinc-800 hover:bg-zinc-700 rounded-lg border border-zinc-700">
                          <iconify-icon icon={copiedId===h.id ? 'solar:check-circle-bold' : 'solar:copy-bold'} className={`text-sm ${copiedId===h.id ? 'text-emerald-400' : 'text-zinc-400'}`}></iconify-icon>
                        </button>
                      </div>

                      {h.uploaded_at && (
                        <p className="text-[9px] text-emerald-600">Upload TikTok: {formatDate(h.uploaded_at)}</p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {!h.uploaded_to_tiktok && (
                        <button onClick={() => handleMarkUploaded(h.id)}
                          className="flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all hover:bg-emerald-500/20">
                          <iconify-icon icon="ri:tiktok-fill" className="text-sm"></iconify-icon>
                          Tandai Uploaded
                        </button>
                      )}
                      {h.storage_url && (
                        <a href={h.storage_url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3 py-2 bg-zinc-800 text-zinc-400 border border-zinc-700 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all hover:text-white">
                          <iconify-icon icon="solar:download-minimalistic-bold" className="text-sm"></iconify-icon>
                          Re-download
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </>)}

    </div>
  );
};

export default TikTokQueueSection;
