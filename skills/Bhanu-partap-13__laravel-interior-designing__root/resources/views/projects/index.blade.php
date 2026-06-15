@extends('layouts.app')

@section('title', __('app.projects.index.eyebrow'))

@section('content')
<section class="page-hero">
    <div class="container">
        <p class="eyebrow">{{ __('app.projects.index.eyebrow') }}</p>
        <h1>{{ __('app.projects.index.title') }}</h1>
        <p class="lead">{{ __('app.projects.index.lead') }}</p>
        @php
            $designer = auth()->user()?->designer;
        @endphp
        @if ($designer)
            <div class="projects-actions">
                <button class="btn btn-emphasis" type="button" data-modal-open="project-modal">
                    Create project
                </button>
            </div>
        @endif
        @if ($projects->count() === 0)
            <div class="placeholder-card">{{ __('app.projects.index.empty') }}</div>
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
            @if (method_exists($projects, 'links'))
                <div class="pagination">{{ $projects->links('partials.pagination') }}</div>
            @endif
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
@if ($designer)
    <div class="modal" id="project-modal" aria-hidden="true">
        <div class="modal-backdrop" data-modal-close></div>
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="project-modal-title">
            <div class="modal-head">
                <div>
                    <p class="eyebrow">New project</p>
                    <h2 id="project-modal-title">New project</h2>
                    <p class="lead">Save your progress as a draft at any step or publish when ready.</p>
                </div>
                <button class="modal-close" type="button" aria-label="Close" data-modal-close>&times;</button>
            </div>
            <form class="modal-form" method="post" action="{{ route('dashboard.projects.store') }}" enctype="multipart/form-data">
                @csrf
                <input type="hidden" name="action" value="draft" data-action-input>
                <input type="hidden" name="redirect_to" value="dashboard.index" data-redirect-input>
                <div class="modal-steps">
                    <div class="modal-step is-active" data-step="1">
                        <label class="field">
                            <span>Title</span>
                            <input type="text" name="title" value="{{ old('title') }}" placeholder="Project title" required>
                        </label>
                        <label class="field">
                            <span>Category</span>
                            <select name="category_id" required>
                                <option value="" disabled selected>Select a category</option>
                                @foreach ($categories as $category)
                                    <option value="{{ $category->id }}">{{ $category->name }}</option>
                                @endforeach
                            </select>
                        </label>
                        <label class="field">
                            <span>Subcategory</span>
                            <select name="subcategory_id">
                                <option value="">Select a subcategory</option>
                                @foreach ($categories as $category)
                                    @if ($category->subcategories->isNotEmpty())
                                        <optgroup label="{{ $category->name }}">
                                            @foreach ($category->subcategories as $subcategory)
                                                <option value="{{ $subcategory->id }}">{{ $subcategory->name }}</option>
                                            @endforeach
                                        </optgroup>
                                    @endif
                                @endforeach
                            </select>
                        </label>
                        <label class="field">
                            <span>Description</span>
                            <textarea name="description" placeholder="Describe the project.">{{ old('description') }}</textarea>
                        </label>
                    </div>
                    <div class="modal-step" data-step="2">
                        <label class="field">
                            <span>Company name</span>
                            <input type="text" name="company_name" value="{{ old('company_name') }}" placeholder="Company name for this project">
                        </label>
                        <label class="field">
                            <span>Budget range</span>
                            <input type="text" name="budget_range" value="{{ old('budget_range') }}" placeholder="Low, Mid, High">
                        </label>
                        <label class="field">
                            <span>Duration (days)</span>
                            <input type="number" name="duration_days" value="{{ old('duration_days') }}" min="1" placeholder="45">
                        </label>
                        <label class="field">
                            <span>Style tags</span>
                            <input type="text" name="style_tags" value="{{ old('style_tags') }}" placeholder="minimal, warm, coastal">
                        </label>
                    </div>
                    <div class="modal-step" data-step="3">
                        <label class="field">
                            <span>Payment status</span>
                            <select name="payment_status">
                                <option value="" disabled selected>Select payment status</option>
                                <option value="paid" @selected(old('payment_status') === 'paid')>Paid</option>
                                <option value="free" @selected(old('payment_status') === 'free')>Free</option>
                            </select>
                        </label>
                        <label class="field">
                            <span>Amount paid</span>
                            <input type="number" name="amount_paid" value="{{ old('amount_paid') }}" min="0" step="0.01" placeholder="0.00">
                        </label>
                    </div>
                    <div class="modal-step" data-step="4">
                        <label class="field">
                            <span>Video</span>
                            <input type="file" name="video" accept="video/*">
                        </label>
                        <label class="field">
                            <span>Before image</span>
                            <input type="file" name="before_image" accept="image/*">
                        </label>
                        <label class="field">
                            <span>After image</span>
                            <input type="file" name="after_image" accept="image/*">
                        </label>
                        <label class="field">
                            <span>Project media</span>
                            <input type="file" name="media[]" accept="image/*,video/*" multiple>
                        </label>
                        <label class="field">
                            <span>Invoice proof (optional)</span>
                            <input type="file" name="invoice_proof" accept="application/pdf,image/*">
                        </label>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-ghost" type="button" data-step-prev>Back</button>
                    <button class="btn btn-ghost" type="button" data-step-next>Next</button>
                    <button class="btn btn-ghost" type="submit" data-action-button="draft" data-redirect="dashboard.index">Save as draft</button>
                    <button class="btn btn-emphasis" type="submit" data-action-button="publish" data-redirect="dashboard.projects.index" data-step-publish>Create project</button>
                </div>
            </form>
        </div>
    </div>
@endif
@endsection
