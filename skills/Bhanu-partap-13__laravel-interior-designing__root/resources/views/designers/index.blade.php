@extends('layouts.app')

@section('title', __('app.designers.index.eyebrow'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.designers.index.eyebrow') }}</p>
        <h1>{{ __('app.designers.index.title') }}</h1>
        <p class="lead">{{ __('app.designers.index.lead') }}</p>
        <div class="filter-row">
            <a class="chip" href="{{ route('designers.index', request()->except('page', 'specialty')) }}">{{ __('app.designers.index.all') }}</a>
            @foreach ($specialties as $specialty)
                <a class="chip" href="{{ route('designers.index', array_merge(request()->except('page', 'specialty'), ['specialty' => $specialty])) }}">
                    {{ $specialty }}
                </a>
            @endforeach
        </div>
        @if ($designers->count() === 0)
            <div class="placeholder-card">{{ __('app.designers.index.empty') }}</div>
        @else
            <div class="card-grid">
                @foreach ($designers as $designer)
                    <article class="card">
                        <div class="card-top">
                            <span class="chip">{{ $designer->specialization ?? __('app.designers.index.specialty_fallback') }}</span>
                            <span class="card-meta">{{ $designer->city ?? __('app.designers.index.city_fallback') }}</span>
                        </div>
                        <img
                            class="card-image"
                            src="{{ $designer->profile_photo ? asset('storage/' . $designer->profile_photo) : 'https://source.unsplash.com/800x600/?interior,studio&sig=' . $designer->id }}"
                            alt="{{ $designer->user?->name ?? __('app.designers.index.specialty_fallback') }}"
                        >
                        <h3>{{ $designer->user?->name ?? __('app.designers.index.specialty_fallback') }}</h3>
                        <p>
                            @if ($designer->years_experience)
                                {{ $designer->years_experience }} {{ __('app.designers.index.years_suffix') }}
                            @else
                                {{ __('app.designers.index.new_studio') }}
                            @endif
                            {{ __('app.designers.index.card_text') }}
                        </p>
                        <div class="card-bottom">
                            <span>{{ $designer->projects_count }} {{ __('app.designers.index.projects_label') }}</span>
                            <a class="text-link" href="{{ route('designers.show', $designer->slug) }}">{{ __('app.designers.index.view_profile') }}</a>
                        </div>
                    </article>
                @endforeach
            </div>
            @if (method_exists($designers, 'links'))
                <div class="pagination">{{ $designers->links('partials.pagination') }}</div>
            @endif
        @endif
    </div>
</section>
@endsection
