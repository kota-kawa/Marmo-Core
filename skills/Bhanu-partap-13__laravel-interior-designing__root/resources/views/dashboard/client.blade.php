@extends('layouts.app')

@section('title', 'Client Dashboard')

@section('content')
<style>
.client-portal-hero {
    background: linear-gradient(120deg, #f9d2c5 0%, #f7e1d2 45%, #f8f0e8 75%, #ffffff 100%);
    padding: 3.5rem 0 2rem;
    border-bottom: 1px solid var(--line);
}

.client-portal-title {
    font-size: clamp(2.2rem, 4vw, 3.4rem);
    margin-bottom: 1rem;
    color: var(--text);
    font-family: var(--font-display);
}

.client-portal-search {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.65rem 1.2rem;
    max-width: 520px;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.06);
}

.client-portal-search svg {
    width: 18px;
    height: 18px;
    color: #6b6b6b;
}

.client-portal-search input {
    border: none;
    background: transparent;
    width: 100%;
    font-size: 0.95rem;
    outline: none;
}

.client-portal-grid {
    display: grid;
    gap: 1.6rem;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.portal-card {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: var(--radius-md);
    padding: 1.5rem;
    box-shadow: 0 16px 30px rgba(0, 0, 0, 0.06);
}

.portal-card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.2rem;
}

.chat-thread {
    display: grid;
    gap: 0.9rem;
}

.chat-bubble {
    padding: 0.85rem 1rem;
    border-radius: 14px;
    font-size: 0.92rem;
    line-height: 1.5;
    background: #f3f4f6;
}

.chat-bubble.chat-out {
    background: #e8edf4;
}

.chat-meta {
    display: block;
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.4rem;
}

.chat-input {
    display: flex;
    gap: 0.6rem;
    margin-top: 1.2rem;
}

.chat-input input {
    flex: 1;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.55rem 0.95rem;
    font-size: 0.9rem;
}

.task-list {
    list-style: none;
    display: grid;
    gap: 1rem;
}

.task-item {
    display: grid;
    grid-template-columns: 20px 1fr auto;
    gap: 0.75rem;
    align-items: center;
}

.task-check {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid #c7cbd3;
    display: inline-block;
}

.task-title {
    font-weight: 600;
    font-size: 0.92rem;
    margin: 0 0 0.3rem;
}

.task-tag {
    display: inline-block;
    font-size: 0.7rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    background: #f3f4f6;
    color: #4b5563;
}

.task-date {
    font-size: 0.75rem;
    color: #8a8f98;
}

.client-form-wrap {
    max-width: 720px;
    margin: 0 auto;
}

.client-form-title {
    margin-bottom: 1rem;
}

.client-form-grid {
    display: grid;
    gap: 1rem;
}

@media (min-width: 760px) {
    .client-form-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .client-form-grid .field.full {
        grid-column: 1 / -1;
    }
}

.field-error {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.85rem;
    color: #b91c1c;
}
</style>

<section class="client-portal-hero">
    <div class="container">
        @if (session('status'))
            <div class="toast" role="status" data-toast style="margin-bottom: 2rem;">
                <span>{{ session('status') }}</span>
                <button class="toast-close" type="button" aria-label="Close" data-toast-close>&times;</button>
            </div>
        @endif
        <h1 class="client-portal-title">Welcome to Client Portal!</h1>
        <div class="client-portal-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7"></circle>
                <path d="M21 21l-4.35-4.35"></path>
            </svg>
            <input type="text" placeholder="Search docs, tasks, files and other with AI..." aria-label="Search">
        </div>
    </div>
</section>

<section class="section" style="padding-top: 2rem;">
    <div class="container client-portal-grid">
        <div class="portal-card">
            <div class="portal-card-head">
                <h3>Client Tasks</h3>
            </div>
            <ul class="task-list">
                <li class="task-item">
                    <span class="task-check"></span>
                    <div>
                        <p class="task-title">Define the target market and audience</p>
                        <span class="task-tag">Analytics</span>
                    </div>
                    <span class="task-date">08/12/2023</span>
                </li>
                <li class="task-item">
                    <span class="task-check"></span>
                    <div>
                        <p class="task-title">Handover the design assets and specifications</p>
                        <span class="task-tag">Design</span>
                    </div>
                    <span class="task-date">08/12/2023</span>
                </li>
                <li class="task-item">
                    <span class="task-check"></span>
                    <div>
                        <p class="task-title">Update project goals and milestones</p>
                        <span class="task-tag">High</span>
                    </div>
                    <span class="task-date">08/18/2023</span>
                </li>
            </ul>
        </div>
    </div>
</section>

<section class="section">
    <div class="container client-form-wrap">
        <form class="form-card" method="post" action="{{ route('client.profile.update') }}" enctype="multipart/form-data">
            @csrf
            @method('PUT')
            <h2 class="client-form-title">Tell us about your project</h2>
            <div class="client-form-grid">
                <label class="field">
                    <span>Design focus</span>
                    <input type="text" name="design_type" required maxlength="120" placeholder="Living room refresh" value="{{ old('design_type', $client->design_type ?? '') }}">
                    @error('design_type')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Budget</span>
                    <input type="text" name="budget_range" required maxlength="60" placeholder="$5,000 - $10,000" value="{{ old('budget_range', $client->budget_range ?? '') }}">
                    @error('budget_range')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Location</span>
                    <input type="text" name="location" required maxlength="120" placeholder="City, State" value="{{ old('location', $client->location ?? '') }}">
                    @error('location')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Timeline</span>
                    <input type="text" name="timeline" required maxlength="120" placeholder="4-6 weeks" value="{{ old('timeline', $client->timeline ?? '') }}">
                    @error('timeline')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Property size</span>
                    <input type="text" name="property_size" required maxlength="120" placeholder="1200 sq ft" value="{{ old('property_size', $client->property_size ?? '') }}">
                    @error('property_size')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field">
                    <span>Style preference</span>
                    <input type="text" name="style_preference" required maxlength="120" placeholder="Modern, Minimal" value="{{ old('style_preference', $client->style_preference ?? '') }}">
                    @error('style_preference')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field full">
                    <span>Notes</span>
                    <textarea name="notes" rows="4" maxlength="2000" placeholder="Key requirements, inspiration, and must-have features.">{{ old('notes', $client->notes ?? '') }}</textarea>
                    @error('notes')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
                <label class="field full">
                    <span>Profile photo</span>
                    <input type="file" name="profile_photo" accept="image/*">
                    @error('profile_photo')
                        <span class="field-error">{{ $message }}</span>
                    @enderror
                </label>
            </div>
            <div style="margin-top: 1.5rem;">
                <button class="btn btn-primary" type="submit">Save Profile</button>
            </div>
        </form>
    </div>
</section>
@endsection
