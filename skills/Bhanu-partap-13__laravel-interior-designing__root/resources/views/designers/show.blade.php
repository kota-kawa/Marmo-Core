@extends('layouts.app')

@section('title', __('app.designers.show.title_fallback'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.designers.show.eyebrow') }}</p>
        @if ($designer->profile_photo)
            <img class="card-image" src="{{ asset('storage/' . $designer->profile_photo) }}" alt="{{ $designer->user?->name ?? __('app.designers.show.title_fallback') }}">
        @endif
        <h1>{{ $designer->user?->name ?? __('app.designers.show.title_fallback') }}</h1>
        <p class="lead">
            {{ $designer->bio ?? __('app.designers.show.bio_fallback') }}
        </p>
        <div class="card-grid">
            <div class="card">
                <h3>{{ __('app.designers.show.snapshot') }}</h3>
                <p>{{ __('app.designers.show.specialty') }}: {{ $designer->specialization ?? __('app.designers.show.specialty_fallback') }}</p>
                <p>{{ __('app.designers.show.city') }}: {{ $designer->city ?? __('app.designers.index.city_fallback') }}</p>
                <p>
                    {{ __('app.designers.show.experience') }}:
                    @if ($designer->years_experience)
                        {{ $designer->years_experience }} {{ __('app.designers.show.experience_suffix') }}
                    @else
                        {{ __('app.designers.show.experience_new') }}
                    @endif
                </p>
            </div>
            <div class="card">
                <h3>{{ __('app.designers.show.services') }}</h3>
                <p>{{ __('app.designers.show.services_line1') }}</p>
                <p>{{ __('app.designers.show.services_line2') }}</p>
            </div>
            <div class="card">
                <h3>{{ __('app.designers.show.contact') }}</h3>
                <p>{{ $designer->user?->email ?? 'parveshyadav136@gmail.com' }}</p>
                <p>{{ $designer->phone ?? '9040011331' }}</p>
                @if ($designer->portfolio_url)
                    <a class="text-link" href="{{ $designer->portfolio_url }}">{{ __('app.designers.show.portfolio') }}</a>
                @endif
            </div>
        </div>
    </div>
</section>

<section class="section">
    <div class="container section-head">
        <div>
            <p class="eyebrow">{{ __('app.designers.show.highlights_eyebrow') }}</p>
            <h2>{{ __('app.designers.show.highlights_title') }}</h2>
        </div>
        <p class="section-lead">{{ __('app.designers.show.highlights_lead') }}</p>
    </div>
    @if ($projects->isEmpty())
        <div class="container">
            <div class="placeholder-card">{{ __('app.designers.show.empty_projects') }}</div>
        </div>
    @else
        <div class="container card-grid">
            @foreach ($projects as $project)
                <article class="card">
                    <div class="card-top">
                        <span class="chip">{{ $project->category?->name ?? __('app.projects.index.project_fallback') }}</span>
                        <span class="card-meta">{{ $designer->city ?? __('app.designers.index.city_fallback') }}</span>
                    </div>
                    <img
                        class="card-image"
                        src="{{ $project->after_image ? asset('storage/' . $project->after_image) : asset('placeholder.svg') }}"
                        alt="{{ $project->title }}"
                    >
                    <h3>{{ $project->title }}</h3>
                    <p>{{ $project->description ?? __('app.projects.index.description_fallback') }}</p>
                    <div class="card-bottom">
                        <span>{{ __('app.designers.show.budget_label') }}: {{ $project->budget_range ?? __('app.projects.show.details_budget_fallback') }}</span>
                        <a class="text-link" href="{{ route('projects.show', $project->slug) }}">{{ __('app.designers.show.view_project') }}</a>
                    </div>
                </article>
            @endforeach
        </div>
    @endif
</section>
@endsection
