<div>
    <div class="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
            <h2 class="text-2xl font-bold text-slate-800 tracking-tight">Detail Pekerjaan Staff IT</h2>
            <p class="text-sm text-slate-500 mt-1">Laporan historis dan pantauan langsung pekerjaan staff.</p>
        </div>
        
        <div class="flex items-center space-x-3">
            <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input wire:model.live.debounce.300ms="search" type="text" class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 w-64" placeholder="Cari ID, Nama, atau Masalah..." />
            </div>

            <select wire:model.live="statusFilter" class="border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 py-2 pl-3 pr-10">
                <option value="">Semua Status</option>
                <option value="open">Open (Menunggu)</option>
                <option value="in_progress">In Progress (Dikerjakan)</option>
                <option value="resolved">Resolved (Selesai)</option>
                <option value="closed">Closed (Ditutup)</option>
            </select>
        </div>
    </div>

    <!-- Table Details -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-slate-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Tiket ID</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Pelapor</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Permasalahan</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status & Waktu</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    @forelse($tickets as $ticket)
                    <tr class="hover:bg-slate-50 transition-colors">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900 border-l-4 {{ $ticket->status === 'resolved' || $ticket->status === 'closed' ? 'border-l-emerald-400' : 'border-l-rose-400' }}">
                            {{ substr($ticket->uuid, 0, 8) }}
                        </td>
                        <td class="px-6 py-4">
                            <div class="text-sm font-bold text-slate-800">{{ $ticket->guest_name ?? 'N/A' }}</div>
                            <div class="text-xs text-slate-500 font-mono mt-0.5">{{ $ticket->guest_nim ?? '-' }}</div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="text-sm font-bold text-slate-800 mb-0.5">{{ $ticket->title }}</div>
                            <div class="text-xs text-indigo-600 font-medium mb-1">{{ optional($ticket->category)->name ?? 'Tanpa Kategori' }}</div>
                            <div class="text-sm text-slate-600 line-clamp-2 italic">"{{ $ticket->description }}"</div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="mb-2">
                                @if($ticket->status === 'open')
                                    <span class="px-2.5 py-1 inline-flex text-xs font-bold rounded-full bg-rose-100 text-rose-700">Open</span>
                                @elseif($ticket->status === 'in_progress')
                                    <span class="px-2.5 py-1 inline-flex text-xs font-bold rounded-full bg-amber-100 text-amber-700">In Progress</span>
                                @elseif($ticket->status === 'resolved')
                                    <span class="px-2.5 py-1 inline-flex text-xs font-bold rounded-full bg-emerald-100 text-emerald-700">Resolved</span>
                                @else
                                    <span class="px-2.5 py-1 inline-flex text-xs font-bold rounded-full bg-slate-100 text-slate-600">Closed</span>
                                @endif
                            </div>
                            <div class="text-xs text-slate-500 flex items-center">
                                <svg class="w-3.5 h-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                {{ $ticket->updated_at->diffForHumans() }}
                            </div>
                        </td>
                    </tr>
                    @empty
                    <tr>
                        <td colspan="4" class="px-6 py-10 text-center text-slate-500">
                            Tidak ada tiket yang ditemukan dengan filter saat ini.
                        </td>
                    </tr>
                    @endforelse
                </tbody>
            </table>
        </div>
        @if($tickets->hasPages())
        <div class="px-6 py-4 border-t border-gray-200">
            {{ $tickets->links() }}
        </div>
        @endif
    </div>
</div>
