@extends('layouts.app')

@section('title', __('app.auth.password.reset_title'))

@section('content')
<section class="page-hero auth-hero">
    <div class="container auth-layout">
        <div class="auth-media auth-media-login" role="img" aria-label="Elegant living room with layered textures"></div>
        <div class="auth-panel">
            <p class="eyebrow">{{ __('app.auth.password.eyebrow') }}</p>
            <h1>{{ __('app.auth.password.reset_heading') }}</h1>
            <p class="lead">{{ __('app.auth.password.reset_lead') }}</p>
            <form class="form-card" method="post" action="{{ route('password.update') }}">
                @csrf
                <input type="hidden" name="token" value="{{ $token }}">
                <label class="field">
                    <span>{{ __('app.auth.password.email') }}</span>
                    <input type="email" name="email" placeholder="{{ __('app.auth.password.email_placeholder') }}" autocomplete="email" value="{{ old('email', $email) }}">
                    @error('email')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.password.password') }}</span>
                    <input type="password" name="password" placeholder="{{ __('app.auth.password.password_placeholder') }}" autocomplete="new-password">
                    @error('password')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.password.password_confirm') }}</span>
                    <input type="password" name="password_confirmation" placeholder="{{ __('app.auth.password.password_confirm_placeholder') }}" autocomplete="new-password">
                </label>
                <button class="btn btn-primary" type="submit">{{ __('app.auth.password.update') }}</button>
            </form>
        </div>
    </div>
</section>
@endsection
