@extends('layouts.app')

@section('title', __('app.dashboard.index.title'))

@section('content')
<section class="page-hero">
    <div class="container">
        @if (session('status'))
            <div class="toast" role="status" data-toast>
                <span>{{ session('status') }}</span>
                <button class="toast-close" type="button" aria-label="Close" data-toast-close>&times;</button>
            </div>
        @endif

        <div class="dashboard-topbar">
            <div class="dashboard-actions">
                <a class="btn btn-primary" href="{{ route('dashboard.projects.index') }}">{{ __('app.dashboard.index.manage_projects') }}</a>
                <a class="btn btn-ghost" href="{{ route('dashboard.inquiries.index') }}">{{ __('app.dashboard.index.view_inquiries') }}</a>
            </div>
            <form method="post" action="{{ route('auth.logout') }}">
                @csrf
                <button class="btn btn-ghost" type="submit">{{ __('app.nav.logout') }}</button>
            </form>
        </div>

        <div class="dashboard-intro">
            @php
                $fullName = $designer?->user?->name ?? __('app.designers.show.title_fallback');
                $nameParts = explode(' ', $fullName, 2);
                $firstName = $nameParts[0] ?? $fullName;
                $lastName = $nameParts[1] ?? '';
            @endphp
            <h1 class="bold-heading">Welcome back, <span class="text-accent">{{ $firstName }}</span></h1>
            <p class="lead">{{ __('app.dashboard.index.lead') }}</p>
        </div>

        {{-- ── PROFILE HERO PANEL ─────────────────────────────────────────── --}}
        <div class="profile-panel-premium">

            {{-- Photo + upload --}}
            <div class="profile-aside">
                <form method="post" action="{{ route('dashboard.profile.update') }}" enctype="multipart/form-data" id="photo-upload-form">
                    @csrf
                    @method('put')
                    <input type="hidden" name="redirect_to" value="dashboard.index">
                    <label class="profile-photo-wrapper" for="profile-photo-input" title="Click to change photo">
                        <div class="profile-photo-large">
                            @if ($designer && $designer->profile_photo)
                                <img src="{{ asset('storage/' . $designer->profile_photo) }}" alt="{{ $fullName }}" id="photo-preview">
                            @else
                                <span class="photo-name" id="photo-name">{{ $fullName }}</span>
                                <img id="photo-preview" style="display:none;" alt="{{ $fullName }}">
                            @endif
                        </div>
                        <input type="file" id="profile-photo-input" name="profile_photo" accept="image/*" class="sr-only">
                    </label>
                    <button type="submit" class="btn btn-ghost photo-upload-btn" id="photo-save-btn" style="display:none; margin-top:0.6rem; font-size:0.85rem;">Save photo</button>
                </form>
            </div>

            {{-- Basic contact info --}}
            <div class="profile-details-main">
                <div class="details-grid">
                    <div class="detail-group">
                        <label>First Name</label>
                        <p>{{ $firstName }}</p>
                    </div>
                    <div class="detail-group">
                        <label>Last Name</label>
                        <p>{{ $lastName ?: '—' }}</p>
                    </div>
                    <div class="detail-group">
                        <label>Email Address</label>
                        <p>{{ $designer?->user?->email }}</p>
                    </div>
                    <div class="detail-group">
                        <label>Phone Number</label>
                        <p>{{ $designer?->phone ?? '—' }}</p>
                    </div>
                </div>
            </div>

            {{-- Published projects stat only --}}
            <div class="profile-stats-brief">
                <div class="brief-stat">
                    <span class="brief-label">{{ __('app.dashboard.index.published_title') }}</span>
                    <span class="brief-value">{{ $projects->where('is_published', true)->count() }}</span>
                </div>
            </div>
        </div>
    </div>
</section>

{{-- ── DESIGN PROFILE DETAILS SECTION ────────────────────────────────── --}}
<section class="section">
    <div class="container">
        <div class="design-profile-section">
            <div class="design-profile-header">
                <div>
                    <p class="eyebrow">Professional Profile</p>
                    <h2>Your Design Details</h2>
                    <p class="section-lead">Your public-facing profile information shown to clients browsing your work.</p>
                </div>
                <button class="btn btn-ghost" id="toggle-edit-btn" type="button">✏️ Edit Profile</button>
            </div>

            {{-- READ VIEW ─────────────────────────────────────── --}}
            <div id="profile-read-view">
                <div class="profile-detail-cards">
                    <div class="profile-detail-card {{ $designer?->bio ? '' : 'is-empty' }}">
                        <span class="pdc-label">Bio / About</span>
                        @if($designer?->bio)
                            <p class="pdc-value">{{ $designer->bio }}</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->specialization ? '' : 'is-empty' }}">
                        <span class="pdc-label">Specialization</span>
                        @if($designer?->specialization)
                            <p class="pdc-value">{{ $designer->specialization }}</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->city ? '' : 'is-empty' }}">
                        <span class="pdc-label">City / Location</span>
                        @if($designer?->city)
                            <p class="pdc-value">{{ $designer->city }}</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->years_experience ? '' : 'is-empty' }}">
                        <span class="pdc-label">Years of Experience</span>
                        @if($designer?->years_experience)
                            <p class="pdc-value">{{ $designer->years_experience }} years</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->education ? '' : 'is-empty' }}">
                        <span class="pdc-label">Education</span>
                        @if($designer?->education)
                            <p class="pdc-value">{{ $designer->education }}</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->certifications ? '' : 'is-empty' }}">
                        <span class="pdc-label">Certifications</span>
                        @if($designer?->certifications)
                            <p class="pdc-value">{{ $designer->certifications }}</p>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                    <div class="profile-detail-card {{ $designer?->portfolio_url ? '' : 'is-empty' }}">
                        <span class="pdc-label">Portfolio URL</span>
                        @if($designer?->portfolio_url)
                            <a class="pdc-value" href="{{ $designer->portfolio_url }}" target="_blank" style="text-decoration: underline;">{{ $designer->portfolio_url }}</a>
                        @else
                            <p class="pdc-empty">Not filled yet</p>
                        @endif
                    </div>
                </div>
            </div>

            {{-- EDIT VIEW (hidden by default) ───────────────────── --}}
            <div id="profile-edit-view" style="display:none;">
                <form class="form-card" method="post" action="{{ route('dashboard.profile.update') }}" enctype="multipart/form-data">
                    @csrf
                    @method('put')
                    <div class="edit-form-grid">
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.bio') }}</span>
                            <textarea name="bio" rows="3" placeholder="{{ __('app.dashboard.profile.bio_placeholder') }}">{{ old('bio', $designer?->bio ?? '') }}</textarea>
                            @error('bio')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.specialization') }}</span>
                            <input type="text" name="specialization" value="{{ old('specialization', $designer?->specialization ?? '') }}" placeholder="{{ __('app.dashboard.profile.specialization_placeholder') }}">
                            @error('specialization')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.city') }}</span>
                            <input type="text" name="city" value="{{ old('city', $designer?->city ?? '') }}" placeholder="{{ __('app.dashboard.profile.city_placeholder') }}">
                            @error('city')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.phone') }}</span>
                            <input type="text" name="phone" value="{{ old('phone', $designer?->phone ?? '') }}" placeholder="{{ __('app.dashboard.profile.phone_placeholder') }}">
                            @error('phone')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.experience') }}</span>
                            <input type="number" name="years_experience" value="{{ old('years_experience', $designer?->years_experience ?? 0) }}" min="0">
                            @error('years_experience')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field">
                            <span>{{ __('app.dashboard.profile.education') }}</span>
                            <input type="text" name="education" value="{{ old('education', $designer?->education ?? '') }}" placeholder="{{ __('app.dashboard.profile.education_placeholder') }}">
                            @error('education')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field" style="grid-column: 1 / -1;">
                            <span>{{ __('app.dashboard.profile.certifications') }}</span>
                            <textarea name="certifications" rows="3" placeholder="{{ __('app.dashboard.profile.certifications_placeholder') }}">{{ old('certifications', $designer?->certifications ?? '') }}</textarea>
                            @error('certifications')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                        <label class="field" style="grid-column: 1 / -1;">
                            <span>{{ __('app.dashboard.profile.portfolio') }}</span>
                            <input type="text" name="portfolio_url" value="{{ old('portfolio_url', $designer?->portfolio_url ?? '') }}" placeholder="{{ __('app.dashboard.profile.portfolio_placeholder') }}">
                            @error('portfolio_url')<span class="form-error">{{ $message }}</span>@enderror
                        </label>
                    </div>
                    <div class="form-actions" style="margin-top: 1.5rem;">
                        <button type="button" class="btn btn-ghost" id="cancel-edit-btn">Cancel</button>
                        <button class="btn btn-primary" type="submit">{{ __('app.dashboard.profile.submit') }}</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</section>

{{-- ── RECENT PROJECTS SECTION ─────────────────────────────────────── --}}
<section class="section dashboard-projects">
    <div class="container">
        <div class="section-head">
            <div>
                <p class="eyebrow">Projects</p>
                <h2>Recent work</h2>
            </div>
            <a class="btn btn-ghost" href="{{ route('dashboard.projects.index') }}">Show more</a>
        </div>
        @if ($projects->isEmpty())
            <div class="placeholder-card">{{ __('app.dashboard.projects.empty_first') }}</div>
        @else
            <div class="project-list">
                @foreach ($projects as $project)
                    <article class="project-item">
                        <div class="project-thumb">
                            <img
                                src="{{ $project->after_image ? asset('storage/' . $project->after_image) : asset('placeholder.svg') }}"
                                alt="{{ $project->title }}"
                            >
                        </div>
                        <div class="project-body">
                            <div class="card-top">
                                <span class="chip">{{ $project->category?->name ?? __('app.dashboard.projects.category_fallback') }}</span>
                                <span class="card-meta">
                                    {{ $project->is_published ? __('app.dashboard.projects.published') : __('app.dashboard.projects.draft') }}
                                </span>
                            </div>
                            <h3>{{ $project->title }}</h3>
                            <p>{{ $project->description ?? __('app.dashboard.projects.description_fallback') }}</p>
                            <div class="project-meta">
                                <span>{{ __('app.dashboard.projects.budget_label') }}: {{ $project->budget_range ?? __('app.projects.show.details_budget_fallback') }}</span>
                                <a class="text-link" href="{{ route('dashboard.projects.edit', $project) }}">Edit project</a>
                            </div>
                        </div>
                    </article>
                @endforeach
            </div>
        @endif
    </div>
</section>

<script>
document.addEventListener('DOMContentLoaded', function () {

    // ── Profile read/edit toggle ──────────────────────
    const toggleBtn  = document.getElementById('toggle-edit-btn');
    const cancelBtn  = document.getElementById('cancel-edit-btn');
    const readView   = document.getElementById('profile-read-view');
    const editView   = document.getElementById('profile-edit-view');

    function showEdit() {
        readView.style.display  = 'none';
        editView.style.display  = 'block';
        toggleBtn.textContent   = '✖ Close editor';
        toggleBtn.setAttribute('aria-expanded', 'true');
        editView.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showRead() {
        editView.style.display  = 'none';
        readView.style.display  = 'block';
        toggleBtn.textContent   = '✏️ Edit Profile';
        toggleBtn.setAttribute('aria-expanded', 'false');
    }

    toggleBtn.addEventListener('click', function () {
        editView.style.display === 'none' ? showEdit() : showRead();
    });

    cancelBtn.addEventListener('click', showRead);

    // Auto-open edit panel if there were validation errors
    @if($errors->any())
    showEdit();
    @endif

    // ── Photo preview & upload ────────────────────────
    const photoInput  = document.getElementById('profile-photo-input');
    const photoSave   = document.getElementById('photo-save-btn');
    const photoPreview = document.getElementById('photo-preview');
    const initials     = document.getElementById('photo-initials');

    if (photoInput) {
        photoInput.addEventListener('change', function () {
            if (!this.files || !this.files[0]) return;
            const reader = new FileReader();
            reader.onload = function (e) {
                if (photoPreview) {
                    photoPreview.src     = e.target.result;
                    photoPreview.style.display = 'block';
                }
                if (initials) initials.style.display = 'none';
                
                // Auto-submit the form as requested
                document.getElementById('photo-upload-form').submit();
            };
            reader.readAsDataURL(this.files[0]);
        });
    }
});
</script>
@endsection
