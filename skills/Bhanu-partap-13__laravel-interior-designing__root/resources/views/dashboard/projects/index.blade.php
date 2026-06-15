@extends('layouts.app')

@section('title', __('app.dashboard.projects.title'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.dashboard.projects.eyebrow') }}</p>
        <h1>{{ __('app.dashboard.projects.heading') }}</h1>
        <p class="lead">{{ __('app.dashboard.projects.lead') }}</p>
        @if (!$profileComplete)
            <div class="status-banner">{{ __('app.dashboard.profile.complete_required') }}</div>
        @endif
        <div class="actions">
            <a class="btn btn-ghost" href="{{ route('dashboard.index') }}">Back to dashboard</a>
        </div>
        @if (session('status'))
            <div class="status-banner">{{ session('status') }}</div>
        @endif
        @if ($projects instanceof \Illuminate\Support\Collection && $projects->isEmpty())
            <div class="placeholder-card">{{ __('app.dashboard.projects.empty_first') }}</div>
        @elseif ($projects->count() === 0)
            <div class="placeholder-card">{{ __('app.dashboard.projects.empty') }}</div>
        @else
            <div class="card-grid">
                @foreach ($projects as $project)
                    <article class="card">
                        <div class="card-top">
                            <span class="chip">{{ $project->category?->name ?? __('app.dashboard.projects.category_fallback') }}</span>
                            <span class="card-meta">{{ $project->is_published ? __('app.dashboard.projects.published') : __('app.dashboard.projects.draft') }}</span>
                        </div>
                        <h3>{{ $project->title }}</h3>
                        <p>{{ $project->description ?? __('app.dashboard.projects.description_fallback') }}</p>
                        <div class="card-bottom">
                            <span>{{ __('app.dashboard.projects.budget_label') }}: {{ $project->budget_range ?? __('app.projects.show.details_budget_fallback') }}</span>
                            <div class="actions">
                                <a class="text-link" href="{{ route('dashboard.projects.edit', $project) }}">{{ __('app.dashboard.projects.edit') }}</a>
                                <form method="post" action="{{ route('dashboard.projects.destroy', $project) }}" onsubmit="return prompt('Please type \'Delete\' to confirm deletion:') === 'Delete';">
                                    @csrf
                                    @method('delete')
                                    <button class="text-link" type="submit">{{ __('app.dashboard.projects.delete') }}</button>
                                </form>
                            </div>
                        </div>
                    </article>
                @endforeach
            </div>
            @if (method_exists($projects, 'links'))
                <div class="pagination">{{ $projects->links('partials.pagination') }}</div>
            @endif
        @endif
    </div>
</section>
@endsection
