@php
$styleTags = old('style_tags', isset($project) && $project->style_tags ? implode(', ', $project->style_tags) : '');
@endphp

<label class="field">
    <span>{{ __('app.dashboard.projects.form.title') }}</span>
    <input type="text" name="title" value="{{ old('title', $project->title ?? '') }}" placeholder="{{ __('app.dashboard.projects.form.title_placeholder') }}">
    @error('title')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.category') }}</span>
    <select name="category_id">
        @foreach ($categories as $category)
            <option value="{{ $category->id }}" @selected(old('category_id', $project->category_id ?? '') == $category->id)>
                {{ $category->name }}
            </option>
        @endforeach
    </select>
    @error('category_id')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.subcategory') ?? 'Subcategory' }}</span>
    <select name="subcategory_id">
        <option value="">Select a subcategory</option>
        @foreach ($categories as $category)
            @if ($category->subcategories->isNotEmpty())
                <optgroup label="{{ $category->name }}">
                    @foreach ($category->subcategories as $subcategory)
                        <option value="{{ $subcategory->id }}" @selected(old('subcategory_id', $project->subcategory_id ?? '') == $subcategory->id)>
                            {{ $subcategory->name }}
                        </option>
                    @endforeach
                </optgroup>
            @endif
        @endforeach
    </select>
    @error('subcategory_id')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.description') }}</span>
    <textarea name="description" placeholder="{{ __('app.dashboard.projects.form.description_placeholder') }}">{{ old('description', $project->description ?? '') }}</textarea>
    @error('description')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.company_name') ?? 'Company name' }}</span>
    <input type="text" name="company_name" value="{{ old('company_name', $project->company_name ?? '') }}" placeholder="Company name for this project">
    @error('company_name')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.budget') }}</span>
    <input type="text" name="budget_range" value="{{ old('budget_range', $project->budget_range ?? '') }}" placeholder="{{ __('app.dashboard.projects.form.budget_placeholder') }}">
    @error('budget_range')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.duration') }}</span>
    <input type="number" name="duration_days" value="{{ old('duration_days', $project->duration_days ?? '') }}" min="1">
    @error('duration_days')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.materials') ?? 'Materials' }}</span>
    <select name="materials">
        <option value="">Select material</option>
        <option value="wood" @selected(old('materials', $project->materials ?? '') === 'wood')>Wood</option>
        <option value="metal" @selected(old('materials', $project->materials ?? '') === 'metal')>Metal</option>
        <option value="glass" @selected(old('materials', $project->materials ?? '') === 'glass')>Glass</option>
        <option value="fabric" @selected(old('materials', $project->materials ?? '') === 'fabric')>Fabric</option>
        <option value="stone" @selected(old('materials', $project->materials ?? '') === 'stone')>Stone</option>
        <option value="other" @selected(old('materials', $project->materials ?? '') === 'other')>Other</option>
    </select>
    @error('materials')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.scope') ?? 'Scope' }}</span>
    <textarea name="scope" placeholder="Briefly describe the project scope">{{ old('scope', $project->scope ?? '') }}</textarea>
    @error('scope')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.tags') }}</span>
    <input type="text" name="style_tags" value="{{ $styleTags }}" placeholder="{{ __('app.dashboard.projects.form.tags_placeholder') }}">
    @error('style_tags')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.payment_status') ?? 'Payment status' }}</span>
    <select name="payment_status">
        <option value="" @selected(!old('payment_status', $project->payment_status ?? ''))>Select payment status</option>
        <option value="paid" @selected(old('payment_status', $project->payment_status ?? '') === 'paid')>Paid</option>
        <option value="free" @selected(old('payment_status', $project->payment_status ?? '') === 'free')>Free</option>
    </select>
    @error('payment_status')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.amount_paid') ?? 'Amount paid' }}</span>
    <input type="number" name="amount_paid" value="{{ old('amount_paid', $project->amount_paid ?? '') }}" min="0" step="0.01" placeholder="0.00">
    @error('amount_paid')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.before') }}</span>
    <input type="file" name="before_image" accept="image/*">
    @error('before_image')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.after') }}</span>
    <input type="file" name="after_image" accept="image/*">
    @error('after_image')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.video') ?? 'Video' }}</span>
    <input type="file" name="video" accept="video/*">
    @error('video')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.media') }}</span>
    <input type="file" name="media[]" accept="image/*,video/*" multiple>
    <p>{{ __('app.dashboard.projects.form.media_help') }}</p>
    @error('media')
        <span class="form-error">{{ $message }}</span>
    @enderror
    @error('media.*')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="field">
    <span>{{ __('app.dashboard.projects.form.invoice') }}</span>
    <input type="file" name="invoice_proof" accept="application/pdf,image/*">
    <p>{{ __('app.dashboard.projects.form.invoice_help') }}</p>
    @error('invoice_proof')
        <span class="form-error">{{ $message }}</span>
    @enderror
</label>
<label class="checkbox">
    <input type="checkbox" name="is_published" value="1" @checked(old('is_published', $project->is_published ?? false))>
    <span>{{ __('app.dashboard.projects.form.publish') }}</span>
</label>
