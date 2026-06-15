@extends('layouts.app')

@section('title', __('app.auth.password.request_title'))

@section('content')
<section class="page-hero auth-hero">
    <div class="container auth-layout">
        <div class="auth-media auth-media-login" role="img" aria-label="Elegant living room with layered textures"></div>
        <div class="auth-panel">
            <p class="eyebrow">{{ __('app.auth.password.eyebrow') }}</p>
            <h1>{{ __('app.auth.password.request_heading') }}</h1>
            <p class="lead">{{ __('app.auth.password.request_lead') }}</p>
            @if (session('status'))
                <div class="status-banner">{{ session('status') }}</div>
            @endif
            <form class="form-card" method="post" action="{{ route('password.email') }}">
                @csrf
                <label class="field">
                    <span>{{ __('app.auth.password.email') }}</span>
                    <input type="email" name="email" placeholder="{{ __('app.auth.password.email_placeholder') }}" autocomplete="email" value="{{ old('email') }}">
                    @error('email')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <button class="btn btn-primary" type="submit">{{ __('app.auth.password.submit') }}</button>
                <a class="text-link" href="{{ route('login') }}">{{ __('app.auth.password.back_to_login') }}</a>
            </form>
        </div>
    </div>
</section>
@endsection
