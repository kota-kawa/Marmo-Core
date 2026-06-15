@extends('layouts.app')

@section('title', __('app.dashboard.inquiries.title'))

@section('content')
@php
$statusLabels = [
    'pending' => __('app.dashboard.inquiries.status_pending'),
    'replied' => __('app.dashboard.inquiries.status_replied'),
    'closed' => __('app.dashboard.inquiries.status_closed'),
];
$hasInquiries = $inquiries instanceof \Illuminate\Support\Collection
    ? $inquiries->isNotEmpty()
    : $inquiries->count() > 0;
@endphp
<section class="page-hero">
    <div class="container"
        data-inquiries-root
        data-designer-id="{{ $designer?->id }}"
        data-inquiry-update-url-base="{{ url('/dashboard/inquiries') }}"
        data-csrf="{{ csrf_token() }}"
        data-status-pending="{{ $statusLabels['pending'] }}"
        data-status-replied="{{ $statusLabels['replied'] }}"
        data-status-closed="{{ $statusLabels['closed'] }}"
        data-label-client="{{ __('app.dashboard.inquiries.client_label') }}"
        data-project-fallback="{{ __('app.projects.index.project_fallback') }}"
        data-visitor-fallback="{{ __('app.dashboard.inquiries.visitor_fallback') }}"
        data-update-label="{{ __('app.dashboard.inquiries.update') }}">
        <p class="eyebrow">{{ __('app.dashboard.inquiries.eyebrow') }}</p>
        <h1>{{ __('app.dashboard.inquiries.heading') }}</h1>
        <p class="lead">{{ __('app.dashboard.inquiries.lead') }}</p>
        <div class="actions">
            <a class="btn btn-ghost" href="{{ route('dashboard.projects.index') }}">{{ __('app.dashboard.inquiries.back_projects') }}</a>
        </div>
        @if (session('status'))
            <div class="status-banner">{{ session('status') }}</div>
        @endif
        <div class="card-grid" data-inquiries-list>
            @foreach ($inquiries as $inquiry)
                <article class="card" data-inquiry-id="{{ $inquiry->id }}">
                    <div class="card-top">
                        <span class="chip">{{ $inquiry->project?->title ?? __('app.projects.index.project_fallback') }}</span>
                        <span class="card-meta">{{ $statusLabels[$inquiry->status] ?? $inquiry->status }}</span>
                    </div>
                    <h3>
                        {{ $inquiry->visitor_name }}
                        @if ($inquiry->client_id)
                            <span class="chip" style="background-color: var(--color-primary); color: white; font-size: 0.7rem; padding: 0.1rem 0.4rem; margin-left: 0.5rem;">{{ __('app.dashboard.inquiries.client_label') }}</span>
                        @endif
                    </h3>
                    <p>{{ $inquiry->visitor_email }}</p>
                    <p>{{ $inquiry->message }}</p>
                    <form class="form-row" method="post" action="{{ route('dashboard.inquiries.update', $inquiry) }}">
                        @csrf
                        @method('patch')
                        <select name="status">
                            <option value="pending" @selected($inquiry->status === 'pending')>{{ __('app.dashboard.inquiries.status_pending') }}</option>
                            <option value="replied" @selected($inquiry->status === 'replied')>{{ __('app.dashboard.inquiries.status_replied') }}</option>
                            <option value="closed" @selected($inquiry->status === 'closed')>{{ __('app.dashboard.inquiries.status_closed') }}</option>
                        </select>
                        <button class="btn btn-ghost" type="submit">{{ __('app.dashboard.inquiries.update') }}</button>
                    </form>
                </article>
            @endforeach
        </div>
        @if (!$hasInquiries)
            <div class="placeholder-card" data-inquiries-empty>{{ __('app.dashboard.inquiries.empty') }}</div>
        @endif
        @if (method_exists($inquiries, 'links'))
            <div class="pagination">{{ $inquiries->links('partials.pagination') }}</div>
        @endif
    </div>
</section>
@endsection
