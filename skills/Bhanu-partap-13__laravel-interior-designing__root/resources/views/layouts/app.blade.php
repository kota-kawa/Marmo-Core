<!doctype html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark">
    @php
        $reverbKey = config('reverb.apps.0.key');
        $reverbHost = env('REVERB_PUBLIC_HOST', env('REVERB_HOST', request()->getHost()));
        $reverbPort = env('REVERB_PUBLIC_PORT', env('REVERB_PORT', request()->getPort()));
        $reverbScheme = env('REVERB_PUBLIC_SCHEME', env('REVERB_SCHEME', request()->getScheme()));
    @endphp
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <meta name="reverb-app-key" content="{{ $reverbKey }}">
    <meta name="reverb-host" content="{{ $reverbHost }}">
    <meta name="reverb-port" content="{{ $reverbPort }}">
    <meta name="reverb-scheme" content="{{ $reverbScheme }}">
    <title>@yield('title', __('app.footer.brand_title'))</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    <div class="page-loader" id="page-loader" role="status" aria-live="polite">
        <div class="loader-stack">
            <div class="loader-mark" aria-hidden="true">
                <span class="loader-letter">R</span>
                <span class="loader-ring"></span>
            </div>
            <div class="loader-text">
                Loading
                <span class="loader-dots" aria-hidden="true">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                </span>
            </div>
        </div>
    </div>
    <div class="page">
        @include('partials.navbar')
        @if ($errors->any())
            <div class="toast" role="alert" data-toast style="background: var(--surface-alt); border-color: #fca5a5; color: #991b1b;">
                <span>{{ $errors->first() }}</span>
                <button class="toast-close" type="button" aria-label="Close" data-toast-close>&times;</button>
            </div>
        @endif
        <main class="main">
            @yield('content')
        </main>
        @include('partials.footer')
    </div>
</body>
</html>
