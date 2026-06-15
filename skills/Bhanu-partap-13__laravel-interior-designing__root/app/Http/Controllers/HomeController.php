<?php

namespace App\Http\Controllers;

use App\Models\Category;
use App\Models\Designer;
use App\Models\Project;
use App\Models\User;

class HomeController extends Controller
{
    public function index()
    {
        // Real stats from the database
        $clientCount   = User::where('role', 'client')->count();
        $projectCount  = Project::where('is_published', true)->count();
        $cityCount     = Designer::whereNotNull('city')
                            ->where('city', '!=', '')
                            ->distinct('city')
                            ->count('city');

        // Real featured projects (latest 3 published)
        $featuredProjects = Project::with(['designer.user', 'category'])
            ->where('is_published', true)
            ->latest()
            ->take(3)
            ->get();

        // Fetch categories for the home page
        $categories = Category::take(10)->get();

        return view('home.index', compact(
            'clientCount',
            'projectCount',
            'cityCount',
            'featuredProjects',
            'categories'
        ));
    }
}
