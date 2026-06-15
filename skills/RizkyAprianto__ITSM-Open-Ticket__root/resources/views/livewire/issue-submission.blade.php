<div class="min-h-screen relative flex items-center justify-center p-4 overflow-hidden bg-slate-50">
    <!-- Gradient Background -->
    <div class="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-slate-100 z-0"></div>
    
    <!-- Abstract Shapes -->
    <div class="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div class="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-400/10 blur-[100px]"></div>
        <div class="absolute bottom-[0%] -right-[10%] w-[60%] h-[60%] rounded-full bg-cyan-400/10 blur-[120px]"></div>
    </div>

    <!-- Main Card -->
    <div class="relative z-10 w-full max-w-lg bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden pt-8 pb-6 px-6 sm:px-8">
        
        <div class="text-center mb-8">
            <div class="mx-auto flex items-center justify-center mb-4">
                <!-- Memanggil gambar logo dari public/images/logo.png -->
                <img src="{{ asset('images/logo.png') }}" alt="Logo Kampus" class="h-20 w-auto object-contain drop-shadow-md">
            </div>
            <h1 class="text-2xl font-bold text-slate-800 tracking-tight">Campus IT Service Center</h1>
            <p class="text-blue-600 mt-2 text-sm font-medium">Sampaikan kendala IT Anda di sini</p>
        </div>

        @if($isSubmitted)
            <!-- Success State -->
            <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-center animate-pulse-slow">
                <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-emerald-100 mb-4">
                    <svg class="h-8 w-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <h3 class="text-xl font-bold text-slate-800 mb-2">Pengaduan Terkirim!</h3>
                <p class="text-slate-600 text-sm mb-4">Tim IT kami akan segera memproses laporan Anda. Simpan nomor tiket di bawah ini untuk pelacakan.</p>
                <div class="bg-white border border-slate-200 shadow-inner rounded-lg p-3 inline-block">
                    <span class="text-slate-800 font-mono font-bold tracking-wider">{{ substr($ticketId, 0, 8) }}</span>
                </div>
                <div class="mt-6">
                    <button wire:click="$set('isSubmitted', false)" class="text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors duration-200">Kirim Laporan Baru</button>
                </div>
            </div>
        @else
            <!-- Form State -->
            <form wire:submit="submit" class="space-y-5">
                
                <!-- User Type Selection -->
                <div class="flex p-1 bg-slate-100 rounded-lg">
                    <button type="button" wire:click="$set('user_type', 'student')" class="flex-1 py-1.5 text-xs font-bold rounded-md transition-all {{ $user_type === 'student' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700' }}">MAHASISWA</button>
                    <button type="button" wire:click="$set('user_type', 'lecturer')" class="flex-1 py-1.5 text-xs font-bold rounded-md transition-all {{ $user_type === 'lecturer' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700' }}">DOSEN</button>
                    <button type="button" wire:click="$set('user_type', 'staff')" class="flex-1 py-1.5 text-xs font-bold rounded-md transition-all {{ $user_type === 'staff' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700' }}">STAFF</button>
                </div>

                <!-- ID Number Input -->
                <div>
                    <label for="id_number" class="block text-sm font-semibold text-slate-700 mb-1">
                        {{ $user_type === 'student' ? 'NIM (Nomor Induk Mahasiswa)' : 'NIP (Nomor Induk Pegawai)' }}
                    </label>
                    <input wire:model="id_number" type="text" id="id_number" class="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-slate-400 shadow-sm" placeholder="e.g. {{ $user_type === 'student' ? '20210331' : '19850101...' }}" />
                    @error('id_number') <span class="text-rose-500 text-xs mt-1 font-medium block">{{ $message }}</span> @enderror
                </div>

                <!-- Name Input -->
                <div>
                    <label for="name" class="block text-sm font-semibold text-slate-700 mb-1">Nama Lengkap</label>
                    <input wire:model="name" type="text" id="name" class="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-slate-400 shadow-sm" placeholder="Nama Lengkap" />
                    @error('name') <span class="text-rose-500 text-xs mt-1 font-medium block">{{ $message }}</span> @enderror
                </div>

                <!-- Phone Input -->
                <div>
                    <label for="phone" class="block text-sm font-semibold text-slate-700 mb-1">Nomor HP (WhatsApp)</label>
                    <input wire:model="phone" type="tel" id="phone" class="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-slate-400 shadow-sm" placeholder="081234567890" />
                    @error('phone') <span class="text-rose-500 text-xs mt-1 font-medium block">{{ $message }}</span> @enderror
                </div>

                <!-- Category Select -->
                <div>
                    <label for="category_id" class="block text-sm font-semibold text-slate-700 mb-1">Kategori Masalah</label>
                    <select wire:model="category_id" id="category_id" class="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-sm">
                        <option value="">Pilih Kategori...</option>
                        @foreach($categories as $category)
                            <option value="{{ $category->id }}">{{ $category->name }}</option>
                        @endforeach
                    </select>
                    @error('category_id') <span class="text-rose-500 text-xs mt-1 font-medium block">{{ $message }}</span> @enderror
                </div>

                <!-- Description Textarea -->
                <div>
                    <label for="description" class="block text-sm font-semibold text-slate-700 mb-1">Deskripsi Kendala</label>
                    <textarea wire:model="description" id="description" rows="4" class="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all placeholder-slate-400 shadow-sm" placeholder="Jelaskan secara detail masalah yang Anda hadapi..."></textarea>
                    @error('description') <span class="text-rose-500 text-xs mt-1 font-medium block">{{ $message }}</span> @enderror
                </div>

                <!-- Submit Button -->
                <div class="pt-2">
                    <button type="submit" class="relative group w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-300 shadow-md hover:shadow-lg overflow-hidden">
                        
                        <span class="relative flex items-center space-x-2">
                            <span wire:loading.remove>
                                <svg class="w-5 h-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                                </svg>
                                Kirim Pengaduan
                            </span>
                            <span wire:loading>
                                <svg class="animate-spin h-5 w-5 mr-3 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Memproses...
                            </span>
                        </span>
                    </button>
                </div>
            </form>
        @endif
        
    </div>
</div>
