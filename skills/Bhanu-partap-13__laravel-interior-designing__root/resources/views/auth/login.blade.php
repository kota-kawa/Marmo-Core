@extends('layouts.app')

@section('title', __('app.auth.login.title'))

@section('content')
<section class="page-hero auth-hero">
    <div class="container auth-layout">
        <div class="auth-media auth-media-login" role="img" aria-label="Elegant living room with layered textures"></div>
        <div class="auth-panel">
            <p class="eyebrow">{{ __('app.auth.login.eyebrow') }}</p>
            <h1>{{ __('app.auth.login.heading') }}</h1>
            <p class="lead">{{ __('app.auth.login.lead') }}</p>
            @if (session('status'))
                <div class="status-banner">{{ session('status') }}</div>
            @endif
            <form class="form-card" method="post" action="{{ route('auth.login.store') }}">
                @csrf
                <label class="field">
                    <span>{{ __('app.auth.login.email') }}</span>
                    <input type="email" name="email" placeholder="{{ __('app.auth.login.email_placeholder') }}" autocomplete="email" value="{{ old('email') }}">
                    @error('email')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.login.password') }}</span>
                    <input type="password" name="password" placeholder="{{ __('app.auth.login.password_placeholder') }}" autocomplete="current-password">
                    @error('password')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <div class="form-row">
                    <label class="checkbox">
                        <input type="checkbox" name="remember" @checked(old('remember'))>
                        <span>{{ __('app.auth.login.remember') }}</span>
                    </label>
                    <a href="{{ route('password.request') }}" class="text-link">{{ __('app.auth.login.forgot') }}</a>
                </div>
                <button class="btn btn-primary" type="submit">{{ __('app.auth.login.submit') }}</button>
            </form>
        </div>
    </div>
</section>
@endsection
