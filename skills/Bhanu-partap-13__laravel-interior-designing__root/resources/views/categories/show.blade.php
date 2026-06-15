@extends('layouts.app')

@section('title', __('app.categories.show.title'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.categories.show.eyebrow') }}</p>
        <h1>{{ $category->name }}</h1>
        <p class="lead">{{ $category->description ?? __('app.categories.show.description_fallback') }}</p>
        @if ($projects->isEmpty())
            <div class="placeholder-card">{{ __('app.categories.show.empty') }}</div>
        @else
            <div class="project-card-grid">
                @foreach ($projects as $project)
                    @php
                        $paymentStatus = strtolower((string) $project->payment_status);
                        $isPaid = $paymentStatus === 'paid' || ($project->amount_paid ?? 0) > 0;
                        $paymentLabel = $isPaid ? 'Paid' : 'Free';
                        $paymentClass = $isPaid ? 'tag-paid' : 'tag-free';
                        $categoryLabel = $project->category?->name ?? __('app.projects.index.project_fallback');
                        $subcategoryLabel = $project->subcategory?->name;
                        $categoryLine = $subcategoryLabel ? $categoryLabel . ' / ' . $subcategoryLabel : $categoryLabel;
                        $designerName = $project->designer?->user?->name ?? __('app.projects.show.meta_designer_fallback');
                        $afterImage = $project->after_image
                            ? Storage::url($project->after_image)
                            : asset('placeholder.svg');
                    @endphp
                    <article class="project-card">
                        <div class="project-card-media">
                            <img
                                class="project-card-image"
                                src="{{ $afterImage }}"
                                alt="{{ $project->title }}"
                            >
                        </div>
                        <div class="project-card-body">
                            <div class="project-card-head">
                                <div>
                                    <p class="project-card-kicker">{{ $categoryLine }}</p>
                                    <h3>{{ $project->title }}</h3>
                                    <p class="project-card-designer">{{ $designerName }}</p>
                                </div>
                                <span class="project-card-tag {{ $paymentClass }}">{{ $paymentLabel }}</span>
                            </div>
                            <p class="project-card-desc">{{ $project->description ?? __('app.projects.index.description_fallback') }}</p>
                            <div class="project-card-meta">
                                <span>{{ __('app.projects.index.budget_prefix') }}: {{ $project->budget_range ?? __('app.projects.show.details_budget_fallback') }}</span>
                                <div class="project-card-actions">
                                    <button
                                        class="btn btn-ghost"
                                        type="button"
                                        data-modal-open="message-modal"
                                        data-project-id="{{ $project->id }}"
                                        data-project-title="{{ $project->title }}"
                                        data-designer-name="{{ $designerName }}"
                                    >
                                        Message designer
                                    </button>
                                    <a class="text-link" href="{{ route('projects.show', $project->slug) }}">{{ __('app.projects.index.view_project') }}</a>
                                </div>
                            </div>
                        </div>
                    </article>
                @endforeach
            </div>
        @endif
    </div>
</section>
<div class="modal" id="message-modal" aria-hidden="true">
    <div class="modal-backdrop" data-modal-close></div>
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="message-modal-title">
        <div class="modal-head">
            <div>
                <p class="eyebrow">Message designer</p>
                <h2 id="message-modal-title">Send a message</h2>
                <p class="lead">
                    You are contacting <strong data-message-designer-name></strong> about
                    <strong data-message-project-title></strong>.
                </p>
            </div>
            <button class="modal-close" type="button" aria-label="Close" data-modal-close>&times;</button>
        </div>
        <form class="modal-form" method="post" action="{{ route('inquiries.store') }}">
            @csrf
            <input type="hidden" name="project_id" data-message-project-id value="">
            <label class="field">
                <span>Your message</span>
                <textarea name="message" rows="5" placeholder="Share your project details and ask a question." required minlength="10" maxlength="2000"></textarea>
            </label>
            <div class="modal-actions" style="justify-content: flex-end;">
                <button class="btn btn-primary" type="submit">Send message</button>
            </div>
        </form>
    </div>
</div>
@endsection
