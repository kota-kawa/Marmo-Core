@extends('layouts.app')

@section('title', __('app.dashboard.profile.title'))

@section('content')
<section class="page-hero">
    <div class="container narrow">
        <p class="eyebrow">{{ __('app.dashboard.profile.eyebrow') }}</p>
        <h1>{{ __('app.dashboard.profile.heading') }}</h1>
        <p class="lead">{{ __('app.dashboard.profile.lead') }}</p>
        @if (session('status'))
            <div class="status-banner">{{ session('status') }}</div>
        @endif
        <form class="form-card" method="post" action="{{ route('dashboard.profile.update') }}" enctype="multipart/form-data">
            @csrf
            @method('put')
            <p>{{ __('app.dashboard.profile.required_hint') }}</p>
            <label class="field">
                <span>{{ __('app.dashboard.profile.bio') }}</span>
                <textarea name="bio" placeholder="{{ __('app.dashboard.profile.bio_placeholder') }}">{{ old('bio', $designer?->bio ?? '') }}</textarea>
                @error('bio')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.specialization') }}</span>
                <input type="text" name="specialization" value="{{ old('specialization', $designer?->specialization ?? '') }}" placeholder="{{ __('app.dashboard.profile.specialization_placeholder') }}">
                @error('specialization')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.city') }}</span>
                <input type="text" name="city" value="{{ old('city', $designer?->city ?? '') }}" placeholder="{{ __('app.dashboard.profile.city_placeholder') }}">
                @error('city')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.phone') }}</span>
                <input type="text" name="phone" value="{{ old('phone', $designer?->phone ?? '') }}" placeholder="{{ __('app.dashboard.profile.phone_placeholder') }}">
                @error('phone')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.portfolio') }}</span>
                <input type="text" name="portfolio_url" value="{{ old('portfolio_url', $designer?->portfolio_url ?? '') }}" placeholder="{{ __('app.dashboard.profile.portfolio_placeholder') }}">
                @error('portfolio_url')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.education') }}</span>
                <input type="text" name="education" value="{{ old('education', $designer?->education ?? '') }}" placeholder="{{ __('app.dashboard.profile.education_placeholder') }}">
                @error('education')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.certifications') }}</span>
                <textarea name="certifications" placeholder="{{ __('app.dashboard.profile.certifications_placeholder') }}">{{ old('certifications', $designer?->certifications ?? '') }}</textarea>
                @error('certifications')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.experience') }}</span>
                <input type="number" name="years_experience" value="{{ old('years_experience', $designer?->years_experience ?? 0) }}" min="0">
                @error('years_experience')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <label class="field">
                <span>{{ __('app.dashboard.profile.photo') }}</span>
                <input type="file" name="profile_photo" accept="image/*">
                @error('profile_photo')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <button class="btn btn-primary" type="submit">{{ __('app.dashboard.profile.submit') }}</button>
        </form>
    </div>
</section>
@endsection
