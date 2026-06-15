@extends('layouts.app')

@section('title', __('app.auth.register.title'))

@section('content')
<section class="page-hero auth-hero">
    <div class="container auth-layout">
        <div class="auth-media auth-media-register" role="img" aria-label="Elegant bedroom interior with soft lighting"></div>
        <div class="auth-panel">
            <p class="eyebrow">{{ __('app.auth.register.eyebrow') }}</p>
            <h1>{{ __('app.auth.register.heading') }}</h1>
            <p class="lead">{{ __('app.auth.register.lead') }}</p>
            <div class="thank-you-message">
                <p>Thank you for choosing to join our community! We're excited to have you here.</p>
            </div>
            @if (session('status'))
                <div class="status-banner">{{ session('status') }}</div>
            @endif
            <form class="form-card" method="post" action="{{ route('auth.register.store') }}">
                @csrf
                <label class="field">
                    <span>{{ __('app.auth.register.role') }}</span>
                    <select name="role">
                        <option value="client" @selected(old('role', 'client') === 'client')>{{ __('app.auth.register.role_client') }}</option>
                        <option value="designer" @selected(old('role') === 'designer')>{{ __('app.auth.register.role_designer') }}</option>
                    </select>
                    @error('role')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.register.name') }}</span>
                    <input type="text" name="name" placeholder="{{ __('app.auth.register.name_placeholder') }}" autocomplete="name" value="{{ old('name') }}">
                    @error('name')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.register.email') }}</span>
                    <input type="email" name="email" placeholder="{{ __('app.auth.register.email_placeholder') }}" autocomplete="email" value="{{ old('email') }}">
                    @error('email')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Mobile number (optional)</span>
                    <input type="tel" name="phone" placeholder="Enter mobile number" autocomplete="tel" value="{{ old('phone') }}">
                    @error('phone')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.register.password') }}</span>
                    <input type="password" name="password" placeholder="{{ __('app.auth.register.password_placeholder') }}" autocomplete="new-password">
                    @error('password')
                        <span class="form-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>{{ __('app.auth.register.password_confirm') }}</span>
                    <input type="password" name="password_confirmation" placeholder="{{ __('app.auth.register.password_confirm_placeholder') }}" autocomplete="new-password">
                </label>
                <button class="btn btn-primary" type="submit">{{ __('app.auth.register.submit') }}</button>
            </form>
        </div>
    </div>
</section>
@endsection
