<?php

namespace App\Http\Controllers;

use App\Models\Category;

class CategoryController extends Controller
{
    public function show(string $category)
    {
        $category = Category::where('slug', $category)->firstOrFail();

        $projects = $category->projects()
            ->with(['designer.user', 'category', 'subcategory'])
            ->where('is_published', true)
            ->latest()
            ->get();

        return view('categories.show', compact('category', 'projects'));
    }
}
