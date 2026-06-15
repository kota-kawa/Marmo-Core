<div>
    <div class="mb-6 flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
        <div class="flex items-center space-x-4 w-full sm:w-auto">
            <input type="text" wire:model.live="search" placeholder="Cari Nama, NIM, atau Judul..." class="border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 rounded-md shadow-sm w-full sm:w-64">
            
            <select wire:model.live="statusFilter" class="border-gray-300 focus:border-indigo-500 focus:ring-indigo-500 rounded-md shadow-sm">
                <option value="">Semua Status</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
            </select>
        </div>
    </div>

    <div class="bg-white shadow rounded-lg overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tiket ID</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Identitas (NIM/NIP)</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nama Pengirim</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kategori & Judul</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Waktu</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Aksi</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                @forelse($tickets as $ticket)
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {{ substr($ticket->uuid, 0, 8) }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-700">
                            {{ $ticket->guest_nim ?? 'N/A' }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                            {{ $ticket->guest_name ?? 'N/A' }}
                        </td>
                        <td class="px-6 py-4">
                            <div class="text-sm text-gray-900 font-bold">{{ $ticket->title }}</div>
                            <div class="text-xs text-blue-600 font-medium mb-1">{{ optional($ticket->category)->name ?? 'Uncategorized' }}</div>
                            <div class="text-sm text-gray-500 line-clamp-2 italic">"{{ $ticket->description }}"</div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <select 
                                wire:change="updateStatus({{ $ticket->id }}, $event.target.value)"
                                class="text-xs font-semibold rounded-full px-2 py-1 border-none focus:ring-2 focus:ring-blue-500
                                {{ $ticket->status === 'open' ? 'bg-red-100 text-red-800' : '' }}
                                {{ $ticket->status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' : '' }}
                                {{ $ticket->status === 'resolved' ? 'bg-green-100 text-green-800' : '' }}
                                {{ $ticket->status === 'closed' ? 'bg-gray-100 text-gray-800' : '' }}
                                ">
                                <option value="open" {{ $ticket->status === 'open' ? 'selected' : '' }}>Open</option>
                                <option value="in_progress" {{ $ticket->status === 'in_progress' ? 'selected' : '' }}>In Progress</option>
                                <option value="resolved" {{ $ticket->status === 'resolved' ? 'selected' : '' }}>Resolved</option>
                                <option value="closed" {{ $ticket->status === 'closed' ? 'selected' : '' }}>Closed</option>
                            </select>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {{ $ticket->created_at->diffForHumans() }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                            <!-- WhatsApp Action -->
                            @if($ticket->guest_phone)
                                <a href="https://wa.me/{{ $ticket->guest_phone }}?text=Halo%20{{ urlencode($ticket->guest_name) }},%20kami%20dari%20Tim%20IT%20Kampus%20terkait%20laporan%20kendala%20Anda..." target="_blank" class="text-green-600 hover:text-green-900 inline-flex items-center">
                                    <svg class="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 24 24"><path d="M11.996 0A12 12 0 0 0 0 12c0 2.115.553 4.103 1.531 5.823L.125 23.875l6.216-1.391A11.961 11.961 0 0 0 11.996 24C18.625 24 24 18.625 24 12S18.625 0 11.996 0zm0 22.008c-1.802 0-3.513-.464-5.06-1.341l-.36-.213-3.766.845.859-3.666-.233-.37c-.966-1.536-1.479-3.32-1.479-5.185 0-5.525 4.492-10.012 10.038-10.012 5.545 0 10.036 4.487 10.036 10.012S17.541 22.008 11.996 22.008zm5.508-7.519c-.302-.152-1.789-.884-2.066-.985-.278-.102-.48-.152-.682.152-.202.304-.783.985-.96 1.187-.177.202-.355.228-.657.076-1.637-.828-2.673-1.602-3.714-3.415-.205-.357.202-.338.794-1.528.076-.153.038-.28-.019-.381-.057-.102-.682-1.644-.935-2.253-.245-.591-.497-.512-.682-.52-.177-.008-.38-.01-.582-.01-.202 0-.53.076-.808.381s-1.06 1.04-1.06 2.537c0 1.497 1.085 2.943 1.237 3.146.152.204 2.146 3.277 5.197 4.593 2.068.892 2.766.974 3.754.821.844-.132 2.686-1.096 3.064-2.155.378-1.059.378-1.966.265-2.155-.113-.189-.417-.303-.719-.455z"/></svg>
                                    Hubungi
                                </a>
                            @endif
                        </td>
                    </tr>
                @empty
                    <tr>
                        <td colspan="6" class="px-6 py-10 text-center text-sm text-gray-500">
                            <div class="flex flex-col items-center justify-center">
                                <svg class="h-10 w-10 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                </svg>
                                Belum ada tiket yang ditemukan.
                            </div>
                        </td>
                    </tr>
                @endforelse
            </tbody>
        </table>
        
        <div class="px-6 py-4 border-t border-gray-200">
            {{ $tickets->links() }}
        </div>
    </div>
</div>
