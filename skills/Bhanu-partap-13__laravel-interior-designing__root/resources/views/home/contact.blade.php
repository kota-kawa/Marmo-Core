@extends('layouts.app')

@section('title', __('app.contact.title'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.contact.eyebrow') }}</p>
        <h1>{{ __('app.contact.title') }}</h1>
        <p class="lead">{{ __('app.contact.lead') }}</p>
        @if (session('status'))
            <div class="toast" role="status" data-toast>
                <span>{{ session('status') }}</span>
                <button class="toast-close" type="button" aria-label="Close" data-toast-close>&times;</button>
            </div>
        @endif
    </div>
</section>

<section class="section">
    <div class="container contact-layout">
        <div class="contact-panel">
            <h2>{{ __('app.contact.panel_title') }}</h2>
            <p class="section-lead">{{ __('app.contact.panel_lead') }}</p>
            <div class="contact-list">
                <div class="contact-item">
                    <span class="chip">{{ __('app.contact.email_label') }}</span>
                    <p>{{ __('app.contact.email_value') }}</p>
                    <a class="text-link" href="mailto:{{ __('app.contact.email_value') }}">{{ __('app.contact.email_action') }}</a>
                </div>
                <div class="contact-item">
                    <span class="chip">{{ __('app.contact.phone_label') }}</span>
                    <p>{{ __('app.contact.phone_value') }}</p>
                    <a class="text-link" href="tel:{{ __('app.contact.phone_value') }}">{{ __('app.contact.phone_action') }}</a>
                </div>
                <div class="contact-item">
                    <span class="chip">{{ __('app.contact.location_label') }}</span>
                    <p>{{ __('app.contact.location_value') }}</p>
                </div>
                <div class="contact-item">
                    <span class="chip">{{ __('app.contact.hours_label') }}</span>
                    <p>{{ __('app.contact.hours_value') }}</p>
                </div>
            </div>
        </div>
        <form id="contact-form" class="form-card" action="{{ route('contact.store') }}" method="post">
            @csrf
            <h3>{{ __('app.contact.form.title') }}</h3>
            <div class="field">
                <label for="contact-name">{{ __('app.contact.form.name') }}</label>
                <input id="contact-name" name="name" type="text" placeholder="{{ __('app.contact.form.name_placeholder') }}" value="{{ old('name') }}" required>
                @error('name')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </div>
            <div class="field">
                <label for="contact-email">{{ __('app.contact.form.email') }}</label>
                <input id="contact-email" name="email" type="email" placeholder="{{ __('app.contact.form.email_placeholder') }}" value="{{ old('email') }}" required>
                @error('email')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </div>
            <div class="field">
                <label for="contact-phone">{{ __('app.contact.form.phone') }}</label>
                <input id="contact-phone" name="phone" type="tel" placeholder="{{ __('app.contact.form.phone_placeholder') }}" value="{{ old('phone') }}">
                @error('phone')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </div>
            <div class="field">
                <label for="contact-message">{{ __('app.contact.form.message') }}</label>
                <textarea id="contact-message" name="message" placeholder="{{ __('app.contact.form.message_placeholder') }}" required>{{ old('message') }}</textarea>
                @error('message')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </div>
            <button class="btn btn-primary" type="submit">{{ __('app.contact.form.submit') }}</button>
            <p class="form-helper">{{ __('app.contact.form.note') }}</p>
        </form>
    </div>
</section>
@endsection
