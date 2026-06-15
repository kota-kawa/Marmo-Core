<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Executive Dashboard - ITSM</title>
    
    @vite(['resources/css/app.css', 'resources/js/app.js'])
    @livewireStyles
    <!-- ApexCharts CDN -->
    <script src="https://cdn.jsdelivr.net/npm/apexcharts" data-navigate-track></script>
</head>
<body class="bg-slate-50 font-sans antialiased text-slate-900">
    <!-- Alpine Root for Layout -->
    <div x-data="{ sidebarOpen: false }" class="flex h-screen overflow-hidden bg-slate-50">
        
        <!-- Mobile Sidebar Overlay -->
        <div x-show="sidebarOpen" x-transition.opacity class="fixed inset-0 z-20 bg-slate-900/50 lg:hidden" @click="sidebarOpen = false"></div>

        <!-- Sidebar -->
        <aside :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'" class="fixed inset-y-0 left-0 z-30 w-64 bg-slate-900 text-slate-300 transition-transform duration-300 lg:static lg:translate-x-0 lg:flex flex-col shadow-2xl">
            <!-- Brand -->
            <div class="flex items-center justify-center h-20 border-b border-slate-800">
                <h2 class="text-2xl font-bold tracking-tight text-white">
                    <span class="text-indigo-400">ITSM</span> Executive
                </h2>
            </div>
            
            <!-- Navigation -->
            <nav class="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
                <!-- Analytics Overview Nav Item -->
                <a href="{{ route('executive.dashboard') }}" wire:navigate class="flex items-center px-4 py-3 font-medium rounded-r-lg transition-colors border-l-4 {{ request()->routeIs('executive.dashboard') ? 'bg-slate-800 text-white border-indigo-500' : 'text-slate-400 hover:bg-slate-800 hover:text-white border-transparent' }}">
                    <svg class="h-5 w-5 mr-3 {{ request()->routeIs('executive.dashboard') ? 'text-indigo-400' : '' }}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                    </svg>
                    Analytics Overview
                </a>
                
                <!-- Detail Pekerjaan Staff Nav Item -->
                <a href="{{ route('executive.staff-work') }}" wire:navigate class="flex items-center px-4 py-3 font-medium rounded-r-lg transition-colors border-l-4 {{ request()->routeIs('executive.staff-work') ? 'bg-slate-800 text-white border-indigo-500' : 'text-slate-400 hover:bg-slate-800 hover:text-white border-transparent' }}">
                    <svg class="h-5 w-5 mr-3 {{ request()->routeIs('executive.staff-work') ? 'text-indigo-400' : '' }}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>
                    </svg>
                    Detail Pekerjaan Staff
                </a>
            </nav>

            <!-- User Profile (Bottom) -->
            <div class="px-6 py-4 border-t border-slate-800 bg-slate-900/50">
                <div class="flex items-center">
                    <div class="h-10 w-10 flex-shrink-0 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold border border-indigo-500/30">
                        {{ strtoupper(substr(auth()->user()->name ?? 'K', 0, 1)) }}
                    </div>
                    <div class="ml-3 truncate">
                        <p class="text-sm font-semibold text-white truncate">{{ auth()->user()->name ?? 'Kepala IT' }}</p>
                        <p class="text-xs font-medium text-slate-400 uppercase tracking-wider truncate">{{ str_replace('_', ' ', auth()->user()->role ?? 'KEPALA_IT') }}</p>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content Area -->
        <div class="flex-1 flex flex-col overflow-hidden w-full">
            <!-- Header -->
            <header class="bg-white shadow-sm z-10 border-b border-slate-200">
                <div class="px-4 sm:px-6 py-4 flex justify-between items-center h-20">
                    <div class="flex items-center">
                        <button @click="sidebarOpen = true" class="text-slate-500 hover:text-slate-700 focus:outline-none lg:hidden mr-4">
                            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                            </svg>
                        </button>
                        <h2 class="text-xl font-bold text-slate-800">Executive Insights</h2>
                    </div>

                    <div class="flex items-center space-x-4">
                        <!-- Notification Bell Placeholder -->
                        <button class="text-slate-400 hover:text-indigo-500 transition-colors focus:outline-none">
                            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                            </svg>
                        </button>

                        <form method="POST" action="{{ route('logout') }}" class="m-0">
                            @csrf
                            <button type="submit" class="flex items-center text-sm px-4 py-2 bg-rose-50 text-rose-600 hover:bg-rose-100 hover:text-rose-700 font-semibold rounded-lg transition-colors border border-rose-100">
                                <span class="hidden sm:inline mr-2">Logout</span>
                                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                </svg>
                            </button>
                        </form>
                    </div>
                </div>
            </header>

            <!-- Main Scrollable Content -->
            <main class="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50 p-4 sm:p-8">
                {{ $slot }}
            </main>
        </div>
    </div>

    @livewireScripts
</body>
</html>
