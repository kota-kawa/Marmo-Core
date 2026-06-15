<?php

namespace App\Http\Controllers;

use App\Models\Category;
use App\Models\Project;
use Illuminate\Http\Request;

class ProjectController extends Controller
{
    public function index(Request $request)
    {
        $categories = Category::with('subcategories')->orderBy('name')->get();

        $projects = Project::with(['designer.user', 'category', 'subcategory'])
            ->where('is_published', true)
            ->when($request->filled('category'), function ($query) use ($request) {
                $query->whereHas('category', function ($categoryQuery) use ($request) {
                    $categoryQuery->where('slug', $request->category);
                });
            })
            ->when($request->filled('city'), function ($query) use ($request) {
                $query->whereHas('designer', function ($designerQuery) use ($request) {
                    $designerQuery->where('city', 'like', '%'.$request->city.'%');
                });
            })
            ->when($request->filled('budget'), function ($query) use ($request) {
                $query->where('budget_range', $request->budget);
            })
            ->when($request->filled('style'), function ($query) use ($request) {
                $query->whereJsonContains('style_tags', $request->style);
            })
            ->latest()
            ->paginate(9)
            ->withQueryString();

        return view('projects.index', compact('projects', 'categories'));
    }

    public function show(string $project)
    {
        $project = Project::with(['designer.user', 'category'])
            ->where('slug', $project)
            ->where('is_published', true)
            ->firstOrFail();

        $project->increment('views_count');

        $related = Project::with(['category', 'designer'])
            ->where('category_id', $project->category_id)
            ->where('id', '!=', $project->id)
            ->where('is_published', true)
            ->limit(3)
            ->get();

        return view('projects.show', compact('project', 'related'));
    }
}
