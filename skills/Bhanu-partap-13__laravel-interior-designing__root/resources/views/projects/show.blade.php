@extends('layouts.app')

@section('title', __('app.projects.show.title'))

@section('content')
@php
$durationLabel = $project->duration_days
    ? ceil($project->duration_days / 7) . ' ' . __('app.projects.show.weeks_suffix')
    : __('app.projects.show.timeline_fallback');
$designerName = $project->designer?->user?->name ?? __('app.projects.show.meta_designer_fallback');
$designerRoute = $project->designer
    ? route('designers.show', $project->designer->slug)
    : route('designers.index');
$galleryItems = $project->gallery ?? [];
$videoExtensions = ['mp4', 'webm', 'mov'];
@endphp
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.projects.show.eyebrow') }}</p>
        <h1>{{ $project->title }}</h1>
        <p class="lead">
            {{ $project->description ?? __('app.projects.show.lead_fallback') }}
        </p>
        <div class="actions">
            <a class="btn btn-primary" href="#inquiry">{{ __('app.projects.show.request_inquiry') }}</a>
            <a class="btn btn-ghost" href="{{ $designerRoute }}">{{ __('app.projects.show.view_designer') }}</a>
        </div>
        <div class="card-grid">
            <div class="card">
                <h3>{{ __('app.projects.show.details_title') }}</h3>
                <p>{{ __('app.projects.show.details_category') }}: {{ $project->category?->name ?? __('app.projects.show.meta_category_fallback') }}</p>
                <p>{{ __('app.projects.show.details_budget') }}: {{ $project->budget_range ?? __('app.projects.show.details_budget_fallback') }}</p>
                <p>{{ __('app.projects.show.details_duration') }}: {{ $durationLabel }}</p>
                <p>{{ __('app.projects.show.details_designer') }}: {{ $designerName }}</p>
            </div>
            @if($project->scope)
                <div class="card">
                    <h3>{{ __('app.projects.show.scope_title') }}</h3>
                    <p>{{ $project->scope }}</p>
                </div>
            @endif
            @if($project->materials)
                <div class="card">
                    <h3>{{ __('app.projects.show.materials_title') }}</h3>
                    <p>{{ ucfirst($project->materials) }}</p>
                </div>
            @endif
        </div>
    </div>
</section>

<section class="section">
    <div class="container section-head">
        <div>
            <p class="eyebrow">{{ __('app.projects.show.gallery_eyebrow') }}</p>
            <h2>{{ __('app.projects.show.gallery_title') }}</h2>
        </div>
        <p class="section-lead">{{ __('app.projects.show.gallery_lead') }}</p>
    </div>
    <div class="container card-grid">
        <article class="card">
            <img
                class="card-image"
                src="{{ $project->before_image ? asset('storage/' . $project->before_image) : asset('placeholder.svg') }}"
                alt="{{ __('app.projects.show.before') }}"
            >
            <p>{{ __('app.projects.show.gallery_before_text') }}</p>
        </article>
        <article class="card">
            <img
                class="card-image"
                src="{{ $project->after_image ? asset('storage/' . $project->after_image) : asset('placeholder.svg') }}"
                alt="{{ __('app.projects.show.after') }}"
            >
            <p>{{ __('app.projects.show.gallery_after_text') }}</p>
        </article>
        @forelse ($galleryItems as $media)
            @php
                $extension = strtolower(pathinfo($media, PATHINFO_EXTENSION));
                $isVideo = in_array($extension, $videoExtensions, true);
            @endphp
            <article class="card">
                @if ($isVideo)
                    <video class="card-image" controls preload="metadata">
                        <source src="{{ asset('storage/' . $media) }}" type="video/{{ $extension === 'mov' ? 'quicktime' : $extension }}">
                    </video>
                @else
                    <img class="card-image" src="{{ asset('storage/' . $media) }}" alt="{{ __('app.projects.show.media') }}">
                @endif
                <p>{{ __('app.projects.show.media_caption') }}</p>
            </article>
        @empty
            <article class="card">
                <img
                    class="card-image"
                    src="https://images.unsplash.com/photo-1501045661006-fcebe0257c3f?auto=format&fit=crop&w=900&q=80"
                    alt="{{ __('app.projects.show.detail') }}"
                >
                <p>{{ __('app.projects.show.gallery_detail_text') }}</p>
            </article>
        @endforelse
    </div>
</section>

<section class="section">
    <div class="container section-head">
        <div>
            <p class="eyebrow">{{ __('app.projects.show.related_eyebrow') }}</p>
            <h2>{{ __('app.projects.show.related_title') }}</h2>
        </div>
        <p class="section-lead">{{ __('app.projects.show.related_lead') }}</p>
    </div>
    @if ($related->isEmpty())
        <div class="container">
            <div class="placeholder-card">{{ __('app.projects.show.related_empty') }}</div>
        </div>
    @else
        <div class="container card-grid">
            @foreach ($related as $relatedProject)
                <article class="card">
                    <div class="card-top">
                        <span class="chip">{{ $relatedProject->category?->name ?? __('app.projects.index.project_fallback') }}</span>
                        <span class="card-meta">{{ $relatedProject->designer?->city ?? __('app.projects.index.city_fallback') }}</span>
                    </div>
                    <img
                        class="card-image"
                        src="{{ $relatedProject->after_image ? asset('storage/' . $relatedProject->after_image) : asset('placeholder.svg') }}"
                        alt="{{ $relatedProject->title }}"
                    >
                    <h3>{{ $relatedProject->title }}</h3>
                    <p>{{ $relatedProject->description ?? __('app.projects.index.description_fallback') }}</p>
                    <div class="card-bottom">
                        <span>{{ __('app.projects.index.budget_prefix') }}: {{ $relatedProject->budget_range ?? __('app.projects.show.details_budget_fallback') }}</span>
                        <a class="text-link" href="{{ route('projects.show', $relatedProject->slug) }}">{{ __('app.projects.index.view_project') }}</a>
                    </div>
                </article>
            @endforeach
        </div>
    @endif
</section>

<section class="section" id="inquiry">
    <div class="container section-head">
        <div>
            <p class="eyebrow">{{ __('app.projects.show.inquiry_eyebrow') }}</p>
            <h2>{{ __('app.projects.show.inquiry_title', ['name' => $designerName]) }}</h2>
        </div>
        <p class="section-lead">{{ __('app.projects.show.inquiry_lead') }}</p>
    </div>
    <div class="container">
        @if (session('status'))
            <div class="status-banner">{{ session('status') }}</div>
        @endif
        <form class="form-card" method="post" action="{{ route('inquiries.store') }}">
            @csrf
            <input type="hidden" name="project_id" value="{{ $project->id }}">
            <label class="field">
                <span>{{ __('app.inquiries.form.message') }}</span>
                <textarea name="message" placeholder="{{ __('app.inquiries.form.message_placeholder') }}">{{ old('message') }}</textarea>
                @error('message')
                    <span class="form-error">{{ $message }}</span>
                @enderror
            </label>
            <button class="btn btn-primary" type="submit">{{ __('app.inquiries.form.submit') }}</button>
        </form>
    </div>
</section>
@endsection
