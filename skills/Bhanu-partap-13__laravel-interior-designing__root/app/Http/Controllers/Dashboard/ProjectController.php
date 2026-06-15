<?php

namespace App\Http\Controllers\Dashboard;

use App\Http\Controllers\Controller;
use App\Http\Requests\StoreProjectRequest;
use App\Http\Requests\UpdateProjectRequest;
use App\Models\Category;
use App\Models\Project;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\Str;

class ProjectController extends Controller
{
    public function index(Request $request)
    {
        $designer = $request->user()->designer;
        $profileComplete = $designer ? $designer->isProfileComplete() : false;

        $projects = $designer
            ? $designer->projects()->with('category')->latest()->paginate(10)
            : collect();

        return view('dashboard.projects.index', compact('projects', 'designer', 'profileComplete'));
    }

    public function create(Request $request)
    {
        $designer = $request->user()->designer;

        if (!$designer || !$designer->isProfileComplete()) {
            return redirect()->route('dashboard.profile.edit')
                ->with('status', __('app.dashboard.profile.complete_required'));
        }

        $categories = Category::with('subcategories')->orderBy('name')->get();

        return view('dashboard.projects.create', compact('categories'));
    }

    public function store(StoreProjectRequest $request): RedirectResponse
    {
        $designer = $request->user()->designer;

        if (!$designer || !$designer->isProfileComplete()) {
            return redirect()->route('dashboard.profile.edit')
                ->with('status', __('app.dashboard.profile.complete_required'));
        }

        $data = $request->validated();
        $slug = $this->uniqueSlug($data['title']);

        $project = new Project();
        $project->fill([
            'designer_id' => $designer->id,
            'category_id' => $data['category_id'],
            'subcategory_id' => $data['subcategory_id'] ?? null,
            'title' => $data['title'],
            'slug' => $slug,
            'description' => $data['description'] ?? null,
            'company_name' => $data['company_name'] ?? null,
            'budget_range' => $data['budget_range'] ?? null,
            'duration_days' => $data['duration_days'] ?? null,
            'style_tags' => $this->parseTags($data['style_tags'] ?? ''),
            'payment_status' => $data['payment_status'] ?? null,
            'amount_paid' => $data['amount_paid'] ?? null,
            'is_published' => $request->input('action') === 'publish',
        ]);

        if ($request->hasFile('before_image')) {
            $project->before_image = $request->file('before_image')->store('projects', 'public');
        }

        if ($request->hasFile('after_image')) {
            $project->after_image = $request->file('after_image')->store('projects', 'public');
        }

        if ($request->hasFile('video')) {
            $project->video = $request->file('video')->store('projects/videos', 'public');
        }

        if ($request->hasFile('invoice_proof')) {
            $project->invoice_proof = $request->file('invoice_proof')->store('projects/invoices', 'public');
        }

        if ($request->hasFile('media')) {
            $project->gallery = $this->storeMediaFiles($request->file('media'));
        }

        $project->save();

        $published = $request->input('action') === 'publish';
        $statusMessage = $published
            ? 'Project published.'
            : 'Draft saved. You can review it on your dashboard.';
        $redirectRoute = $request->input('redirect_to');

        if ($redirectRoute && Route::has($redirectRoute)) {
            return redirect()->route($redirectRoute)
                ->with('status', $statusMessage);
        }

        return redirect()->route('dashboard.projects.index')
            ->with('status', $statusMessage);
    }

    public function edit(Project $project, Request $request)
    {
        $this->ensureOwner($project, $request);

        $categories = Category::with('subcategories')->orderBy('name')->get();

        return view('dashboard.projects.edit', compact('project', 'categories'));
    }

    public function update(UpdateProjectRequest $request, Project $project): RedirectResponse
    {
        $this->ensureOwner($project, $request);

        $data = $request->validated();

        if ($project->title !== $data['title']) {
            $project->slug = $this->uniqueSlug($data['title'], $project->id);
        }

        $project->fill([
            'category_id' => $data['category_id'],
            'subcategory_id' => $data['subcategory_id'] ?? null,
            'title' => $data['title'],
            'description' => $data['description'] ?? null,
            'company_name' => $data['company_name'] ?? null,
            'budget_range' => $data['budget_range'] ?? null,
            'duration_days' => $data['duration_days'] ?? null,
            'style_tags' => $this->parseTags($data['style_tags'] ?? ''),
            'payment_status' => $data['payment_status'] ?? null,
            'amount_paid' => $data['amount_paid'] ?? null,
            'is_published' => $request->input('action') === 'publish',
        ]);

        if ($request->hasFile('before_image')) {
            $this->deleteFile($project->before_image);
            $project->before_image = $request->file('before_image')->store('projects', 'public');
        }

        if ($request->hasFile('after_image')) {
            $this->deleteFile($project->after_image);
            $project->after_image = $request->file('after_image')->store('projects', 'public');
        }

        if ($request->hasFile('video')) {
            $this->deleteFile($project->video);
            $project->video = $request->file('video')->store('projects/videos', 'public');
        }

        if ($request->hasFile('invoice_proof')) {
            $this->deleteFile($project->invoice_proof);
            $project->invoice_proof = $request->file('invoice_proof')->store('projects/invoices', 'public');
        }

        if ($request->hasFile('media')) {
            $media = $this->storeMediaFiles($request->file('media'));
            $existing = $project->gallery ?? [];
            $project->gallery = array_values(array_merge($existing, $media));
        }

        $project->save();

        return redirect()->route('dashboard.projects.index')
            ->with('status', 'Project updated.');
    }

    public function destroy(Project $project, Request $request): RedirectResponse
    {
        $this->ensureOwner($project, $request);

        $this->deleteFile($project->before_image);
        $this->deleteFile($project->after_image);
        $this->deleteFile($project->video);
        $this->deleteFile($project->invoice_proof);
        $this->deleteGallery($project->gallery);

        $project->delete();

        return redirect()->route('dashboard.projects.index')
            ->with('status', 'Project deleted.');
    }

    private function ensureOwner(Project $project, Request $request): void
    {
        $designer = $request->user()->designer;

        if (!$designer || $project->designer_id !== $designer->id) {
            abort(403, 'Not authorized to manage this project.');
        }
    }

    private function uniqueSlug(string $title, ?int $ignoreId = null): string
    {
        $base = Str::slug($title);
        $slug = $base;
        $counter = 1;

        while (
            Project::where('slug', $slug)
                ->when($ignoreId, fn($query) => $query->where('id', '!=', $ignoreId))
                ->exists()
        ) {
            $slug = $base.'-'.$counter;
            $counter++;
        }

        return $slug;
    }

    private function parseTags(string $tags): ?array
    {
        $parsed = array_filter(array_map('trim', explode(',', $tags)));

        return $parsed ?: null;
    }

    private function deleteFile(?string $path): void
    {
        if ($path && Storage::disk('public')->exists($path)) {
            Storage::disk('public')->delete($path);
        }
    }

    private function storeMediaFiles(array $files): array
    {
        $stored = [];

        foreach ($files as $file) {
            $stored[] = $file->store('projects/media', 'public');
        }

        return $stored;
    }

    private function deleteGallery(?array $gallery): void
    {
        if (!$gallery) {
            return;
        }

        foreach ($gallery as $path) {
            $this->deleteFile($path);
        }
    }
}
